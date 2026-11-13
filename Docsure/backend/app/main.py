import json
import httpx
from openai import OpenAI
import os
import uuid
import hashlib
import secrets

from pathlib import Path
from datetime import datetime, date
from typing import Optional

from bson import ObjectId
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from fastapi import (
    FastAPI, File, HTTPException, UploadFile,
    Request, Response, Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pymongo import MongoClient
from pydantic import BaseModel, EmailStr

from app.services.expiry import get_expiry_details
from app.services.intelligence import (
    classify_document,
    extract_dates,
    extract_text_from_file,
    suggest_expiry_date
)

load_dotenv()

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg"}

SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET is missing from backend/.env")

COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE", "false"
).lower() == "true"

COOKIE_NAME = "docusure_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7

app = FastAPI(
    title="Docusure API",
    version="2.0.0"
)

origin = os.getenv(
    "FRONTEND_ORIGIN",
    "http://localhost:5173"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

serializer = URLSafeTimedSerializer(
    SESSION_SECRET,
    salt="docusure-auth"
)

client = None
db = None
collection = None
users_collection = None
notifications_collection = None

try:
    client = MongoClient(
        os.getenv(
            "MONGODB_URI",
            "mongodb://localhost:27017"
        ),
        serverSelectionTimeoutMS=2500
    )

    client.admin.command("ping")

    db = client[
        os.getenv("MONGODB_DATABASE", "docosure")
    ]

    collection = db["documents"]
    users_collection = db["users"]
    notifications_collection = db["notifications"]

    users_collection.create_index(
        "email", unique=True
    )

    collection.create_index("user_id")
    collection.create_index("expiry_date")

    notifications_collection.create_index("user_id")

    print("MongoDB connected successfully.")

except Exception as exc:
    print(f"MongoDB connection error: {exc}")


# ---------------- MODELS ----------------

class RegisterPayload(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class DocumentUpdate(BaseModel):
    category: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None


# ---------------- DATABASE ----------------

def get_db_collection(coll):
    if coll is None:
        raise HTTPException(
            status_code=503,
            detail="MongoDB is unavailable."
        )

    return coll


# ---------------- PASSWORD SECURITY ----------------

def hash_password(password):
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310000
    )

    return (
        f"pbkdf2_sha256${salt.hex()}${digest.hex()}"
    )


def verify_password(password, stored):
    try:
        algorithm, salt_hex, digest_hex = stored.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            310000
        )

        return secrets.compare_digest(
            digest.hex(),
            digest_hex
        )

    except (ValueError, TypeError):
        return False


# ---------------- SESSION ----------------

def set_session(response, user_id):
    token = serializer.dumps({
        "user_id": user_id
    })

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/"
    )


def get_current_user(request: Request):
    users = get_db_collection(users_collection)

    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Please log in."
        )

    try:
        data = serializer.loads(
            token,
            max_age=SESSION_MAX_AGE
        )

        user_id = data.get("user_id")

    except (BadSignature, SignatureExpired):
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please log in again."
        )

    if not user_id or not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=401,
            detail="Invalid session."
        )

    user = users.find_one({
        "_id": ObjectId(user_id)
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found."
        )

    return user


def public_user(user):
    return {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "user")
    }


# ---------------- DOCUMENT SERIALIZATION ----------------

def serialize(doc):
    expiry_details = None

    if doc.get("expiry_date"):
        try:
            expiry_details = get_expiry_details(
                doc["expiry_date"]
            )
        except (ValueError, TypeError):
            pass

    return {
        "id": str(doc["_id"]),
        "filename": doc.get("filename", ""),
        "category": doc.get("category", "Other"),
        "confidence": doc.get("confidence", 0),
        "uploaded_at": doc.get("uploaded_at", ""),
        "expiry_date": doc.get("expiry_date"),

        "remaining_days": (
            expiry_details["remaining_days"]
            if expiry_details else None
        ),

        "dates_found": doc.get("dates_found", []),
        "extracted_text": doc.get("extracted_text", ""),
        "notes": doc.get("notes", ""),

        "status": (
            expiry_details["status"]
            if expiry_details
            else doc.get("status", "Needs review")
        ),

        "file_url": (
            f"/api/documents/{str(doc['_id'])}/file"
        )
    }


# ---------------- HEALTH ----------------

@app.get("/api/health")
def health():
    mongo_ok = False

    try:
        if client:
            client.admin.command("ping")
            mongo_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "mongodb": mongo_ok,
        "app": "Docusure API"
    }


# ---------------- REGISTER ----------------

@app.post("/api/auth/register")
def register(
    payload: RegisterPayload,
    response: Response
):
    users = get_db_collection(users_collection)

    name = payload.name.strip()
    email = str(payload.email).lower().strip()

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Enter your full name."
        )

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters."
        )

    if users.find_one({"email": email}):
        raise HTTPException(
            status_code=409,
            detail="Email already registered."
        )

    role = (
        "admin"
        if users.count_documents({}) == 0
        else "user"
    )

    user = {
        "name": name,
        "email": email,
        "password_hash": hash_password(
            payload.password
        ),
        "role": role,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }

    try:
        result = users.insert_one(user)
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="Could not create account. Check whether the email is already registered."
        )

    user["_id"] = result.inserted_id    


    return {
        "user": public_user(user),
        "message": "Account created successfully."
    }


# ---------------- LOGIN ----------------

@app.post("/api/auth/login")
def login(
    payload: LoginPayload,
    response: Response
):
    users = get_db_collection(users_collection)

    email = str(payload.email).lower().strip()

    user = users.find_one({
        "email": email
    })

    if (
        not user
        or not verify_password(
            payload.password,
            user.get("password_hash", "")
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    set_session(
        response,
        str(user["_id"])
    )

    return {
        "user": public_user(user),
        "message": "Welcome back."
    }


# ---------------- CURRENT USER ----------------

@app.get("/api/auth/me")
def auth_me(user=Depends(get_current_user)):
    return {
        "user": public_user(user)
    }


# ---------------- LOGOUT ----------------

@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax"
    )

    return {
        "message": "Logged out successfully."
    }


# ---------------- UPLOAD DOCUMENT ----------------

@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    dbcol = get_db_collection(collection)

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, PNG and JPG files are supported."
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_UPLOAD_MB} MB."
        )

    safe_name = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / safe_name

    destination.write_bytes(content)

    try:
        extracted = extract_text_from_file(destination)

        category, confidence = classify_document(
            extracted,
            file.filename or ""
        )

        dates = extract_dates(extracted)

        expiry = suggest_expiry_date(extracted)

        record = {
            "user_id": str(user["_id"]),
            "filename": Path(
                file.filename or safe_name
            ).name,
            "stored_name": safe_name,
            "category": category,
            "confidence": confidence,
            "uploaded_at": (
                datetime.utcnow().isoformat() + "Z"
            ),
            "expiry_date": expiry,
            "dates_found": dates,
            "extracted_text": extracted[:50000],
            "notes": "",
            "status": "Needs review"
        }

        result = dbcol.insert_one(record)

        record["_id"] = result.inserted_id

        return {
            "document": serialize(record),
            "message": "Document uploaded successfully."
        }

    except Exception as exc:
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {exc}"
        )


# ---------------- LIST DOCUMENTS ----------------

@app.get("/api/documents")
def list_documents(
    q: str = "",
    category: str = "",
    user=Depends(get_current_user)
):
    dbcol = get_db_collection(collection)

    query = {
        "user_id": str(user["_id"])
    }

    if category and category != "All":
        query["category"] = category

    if q.strip():
        query["$and"] = [
            {"user_id": str(user["_id"])},
            {
                "$or": [
                    {
                        "filename": {
                            "$regex": q.strip(),
                            "$options": "i"
                        }
                    },
                    {
                        "extracted_text": {
                            "$regex": q.strip(),
                            "$options": "i"
                        }
                    },
                    {
                        "category": {
                            "$regex": q.strip(),
                            "$options": "i"
                        }
                    }
                ]
            }
        ]

    docs = list(
        dbcol.find(query)
        .sort("uploaded_at", -1)
        .limit(200)
    )

    return [
        serialize(doc)
        for doc in docs
    ]


# ---------------- SINGLE DOCUMENT ----------------

@app.get("/api/documents/{document_id}")
def get_document(
    document_id: str,
    user=Depends(get_current_user)
):
    dbcol = get_db_collection(collection)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    doc = dbcol.find_one({
        "_id": ObjectId(document_id),
        "user_id": str(user["_id"])
    })

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return serialize(doc)


# ---------------- ORIGINAL FILE ----------------

@app.get("/api/documents/{document_id}/file")
def get_document_file(
    document_id: str,
    user=Depends(get_current_user)
):
    dbcol = get_db_collection(collection)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    doc = dbcol.find_one({
        "_id": ObjectId(document_id),
        "user_id": str(user["_id"])
    })

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    path = UPLOAD_DIR / doc.get("stored_name", "")

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Stored file is missing."
        )

    return FileResponse(
        path,
        filename=doc.get("filename", "document")
    )


# ---------------- UPDATE DOCUMENT ----------------

@app.patch("/api/documents/{document_id}")
def update_document(
    document_id: str,
    payload: DocumentUpdate,
    user=Depends(get_current_user)
):
    dbcol = get_db_collection(collection)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    updates = payload.dict(exclude_unset=True)

    if "expiry_date" in updates and updates["expiry_date"]:
        try:
            date.fromisoformat(
                updates["expiry_date"]
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Expiry date must use YYYY-MM-DD."
            )

    result = dbcol.update_one(
        {
            "_id": ObjectId(document_id),
            "user_id": str(user["_id"])
        },
        {"$set": updates}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return get_document(document_id, user)


# ---------------- DELETE DOCUMENT ----------------

@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: str,
    user=Depends(get_current_user)
):
    dbcol = get_db_collection(collection)

    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID."
        )

    doc = dbcol.find_one_and_delete({
        "_id": ObjectId(document_id),
        "user_id": str(user["_id"])
    })

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    (UPLOAD_DIR / doc.get(
        "stored_name", ""
    )).unlink(missing_ok=True)

    return {
        "message": "Document deleted."
    }


# ---------------- EXPIRY ALERTS ----------------

@app.get("/api/alerts")
def alerts(user=Depends(get_current_user)):
    dbcol = get_db_collection(collection)

    today = date.today()

    docs = list(
        dbcol.find({
            "user_id": str(user["_id"]),
            "expiry_date": {"$ne": None}
        }).limit(500)
    )

    output = []

    for doc in docs:
        try:
            expiry = date.fromisoformat(
                str(doc["expiry_date"])[:10]
            )

            days = (expiry - today).days

            if days <= 30:
                item = serialize(doc)

                item["days_remaining"] = days

                item["alert_type"] = (
                    "Expired" if days < 0
                    else "Due soon"
                )

                output.append(item)

        except (ValueError, TypeError):
            continue

    return sorted(
        output,
        key=lambda item: item["days_remaining"]
    )


# ---------------- DASHBOARD ----------------

@app.get("/api/dashboard")
def dashboard(user=Depends(get_current_user)):
    dbcol = get_db_collection(collection)

    docs = list(
        dbcol.find({
            "user_id": str(user["_id"])
        }, {
            "category": 1,
            "expiry_date": 1
        }).limit(2000)
    )

    today = date.today()

    expired = 0
    due_soon = 0
    categories = {}

    for doc in docs:
        category = doc.get("category", "Other")

        categories[category] = (
            categories.get(category, 0) + 1
        )

        try:
            if doc.get("expiry_date"):
                days = (
                    date.fromisoformat(
                        str(doc["expiry_date"])[:10]
                    ) - today
                ).days

                if days < 0:
                    expired += 1

                elif days <= 30:
                    due_soon += 1

        except (ValueError, TypeError):
            continue

    return {
        "total_documents": len(docs),
        "expired": expired,
        "due_soon": due_soon,
        "categories": [
            {"name": key, "count": value}
            for key, value in sorted(categories.items())
        ]
    }


# ---------------- SEARCH ----------------

@app.get("/api/search")
def search(
    q: str,
    user=Depends(get_current_user)
):
    if not q.strip():
        return []

    return list_documents(q=q, user=user)


# ---------------- DOCUSURE AI ASSISTANT ----------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")


class AssistantChatPayload(BaseModel):
    message: str


@app.post("/api/assistant/chat")
def assistant_chat(
    payload: AssistantChatPayload,
    user=Depends(get_current_user)
):
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI assistant is not configured. Add OPENAI_API_KEY to backend/.env."
        )

    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please enter a message.")

    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="Message is too long. Keep it under 4,000 characters.")

    ai_client = OpenAI(api_key=OPENAI_API_KEY)
    user_id = str(user["_id"])
    actions = []

    tools = [
        {
            "type": "function",
            "name": "get_dashboard_summary",
            "description": "Get the signed-in user's document dashboard counts and category summary.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            "strict": True
        },
        {
            "type": "function",
            "name": "search_user_documents",
            "description": "Search only the signed-in user's documents by filename, category, or extracted document text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search phrase, document name, or identifying term."},
                    "category": {"type": "string", "description": "Optional exact category; use an empty string when not specified."}
                },
                "required": ["query", "category"],
                "additionalProperties": False
            },
            "strict": True
        },
        {
            "type": "function",
            "name": "get_expiry_alerts",
            "description": "Get the signed-in user's expired and soon-to-expire document alerts.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            "strict": True
        },
        {
            "type": "function",
            "name": "navigate_to_page",
            "description": "Navigate the user's DocuSure interface to a page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "string", "enum": ["Overview", "Documents", "Expiry alerts"]}
                },
                "required": ["page"],
                "additionalProperties": False
            },
            "strict": True
        },
        {
            "type": "function",
            "name": "open_user_document",
            "description": "Open one of the signed-in user's documents in the document review panel. First search for the document if its ID is not known.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"}
                },
                "required": ["document_id"],
                "additionalProperties": False
            },
            "strict": True
        }
    ]

    instructions = """
You are DocuSure Assistant, an agentic guide inside the DocuSure document-management application.

Your job is to help the signed-in user understand and manage their own documents and navigate the app.
Use the available tools whenever the user asks about their documents, counts, categories, or expiry alerts.
Never guess document details, counts, expiry dates, or search results. If the tools do not find something, say so.
Only discuss information returned for the currently signed-in user. Never claim access to another user's data.
When the user asks to go to a page, call navigate_to_page.
When the user asks to open a particular document, search for it first if needed, then call open_user_document with the returned ID.
Explain clearly what you did. Do not claim to upload, edit, delete, renew, email, or otherwise change a document; those actions are not available through this assistant.
Do not ask for passwords, API keys, or other secrets.
Keep responses helpful and concise.
"""

    def run_tool(name, arguments):
        if name == "get_dashboard_summary":
            return dashboard(user)

        if name == "search_user_documents":
            query = arguments.get("query", "").strip()
            category = arguments.get("category", "").strip()
            docs = list_documents(q=query, category=category, user=user)
            results = []
            for doc in docs[:20]:
                results.append({
                    "id": doc.get("id"),
                    "filename": doc.get("filename"),
                    "category": doc.get("category"),
                    "expiry_date": doc.get("expiry_date"),
                    "status": doc.get("status"),
                    "remaining_days": doc.get("remaining_days")
                })
            return {"count": len(docs), "documents": results}

        if name == "get_expiry_alerts":
            return alerts(user)

        if name == "navigate_to_page":
            page = arguments["page"]
            actions.append({"type": "navigate", "page": page})
            return {"success": True, "page": page, "message": f"Navigate to {page}."}

        if name == "open_user_document":
            document_id = arguments["document_id"]
            if not ObjectId.is_valid(document_id):
                return {"success": False, "message": "Invalid document ID."}

            doc = get_db_collection(collection).find_one({
                "_id": ObjectId(document_id),
                "user_id": user_id
            })
            if not doc:
                return {"success": False, "message": "Document not found in this user's account."}

            document = serialize(doc)
            actions.append({"type": "open_document", "document": document})
            actions.append({"type": "navigate", "page": "Documents"})
            return {"success": True, "document": document, "message": "Document opened in the review panel."}

        return {"error": "Unknown tool."}

    try:
        response = ai_client.responses.create(
            model=OPENAI_MODEL,
            instructions=instructions,
            input=[{"role": "user", "content": message}],
            tools=tools
        )

        for _ in range(4):
            function_calls = [
                item for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                break

            next_input = list(response.output)

            for call in function_calls:
                try:
                    arguments = json.loads(call.arguments or "{}")
                    result = run_tool(call.name, arguments)
                except Exception as tool_error:
                    result = {"error": str(tool_error)}

                next_input.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, default=str)
                })

            response = ai_client.responses.create(
                model=OPENAI_MODEL,
                instructions=instructions,
                input=next_input,
                tools=tools
            )

        reply = (response.output_text or "").strip()
        if not reply:
            reply = "I couldn't produce a response. Please try asking in a different way."

        return {"reply": reply, "actions": actions}

    except Exception as exc:
        print(f"DocuSure assistant error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="The AI assistant could not complete the request. Check the OpenAI API key, model access, and backend terminal for details."
        )
    