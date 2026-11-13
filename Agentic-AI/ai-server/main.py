
import httpx
import os
import json
import shutil
import secrets

from fastapi.staticfiles import StaticFiles
from datetime import datetime
from rag import process_pdf, list_documents
from fastapi import (
    FastAPI,
    Request,
    UploadFile,
    File,
    HTTPException,
    Depends
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from agent import run_agent


# ==========================================
# CREATE FASTAPI APPLICATION
# ==========================================

app = FastAPI(title="My Open AI Server")
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")


# ==========================================
# API KEY AUTHENTICATION
# ==========================================

API_KEY = os.getenv("API_KEY", "my-secret-key-123")


def require_key(req: Request):
    key = req.headers.get("x-api-key")

    if not key or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )


# ==========================================
# CORS CONFIGURATION
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# OLLAMA CONFIGURATION
# ==========================================

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"

DEFAULT_MODEL = "qwen2.5:3b"


# ==========================================
# QUERY LOGGING
# ==========================================

LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "queries.jsonl")


def log_query(messages):

    entry = {
        "timestamp": datetime.now().isoformat(),
        "messages": messages
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ==========================================
# HOME ROUTE
# ==========================================

@app.get("/")
async def home():

    return {
        "message": "My Open AI Server is running!"
    }


# ==========================================
# MODEL LIST ROUTE
# ==========================================

@app.get("/v1/models")
async def models():

    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL,
                "object": "model"
            }
        ]
    }


# ==========================================
# DAY 1: NORMAL CHAT COMPLETIONS
# ==========================================

@app.post("/v1/chat/completions")
async def chat_completions(req: Request):

    body = await req.json()

    body.setdefault("model", DEFAULT_MODEL)

    if body.get("stream", False):

        async def generate():

            async with httpx.AsyncClient(timeout=None) as client:

                async with client.stream(
                    "POST",
                    OLLAMA_URL,
                    json=body
                ) as response:

                    async for chunk in response.aiter_raw():
                        yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

    async with httpx.AsyncClient(timeout=None) as client:

        response = await client.post(
            OLLAMA_URL,
            json=body
        )

    return JSONResponse(
        content=response.json(),
        status_code=response.status_code
    )


# ==========================================
# DAY 2: AI AGENT CHAT
# ==========================================

@app.post("/agent/chat")
async def agent_chat(
    req: Request,
    _: None = Depends(require_key)
):

    body = await req.json()

    messages = body.get("messages", [])

    log_query(messages)

    return await run_agent(messages)


# ==========================================
# DAY 3: PDF DOCUMENT UPLOAD
# ==========================================

UPLOAD_DIR = "uploaded_documents"

MAX_FILE_SIZE = 10 * 1024 * 1024

os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    _: None = Depends(require_key)
):

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    contents = await file.read(MAX_FILE_SIZE + 1)

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10 MB."
        )

    await file.seek(0)

    filename = os.path.basename(file.filename)

    file_path = os.path.join(UPLOAD_DIR, filename)

    try:

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = process_pdf(file_path, filename)

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        await file.close()


# ==========================================
# DAY 3: LIST UPLOADED DOCUMENTS
# ==========================================

@app.get("/documents")
async def get_documents(
    _: None = Depends(require_key)
):

    return {
        "documents": list_documents()
    }
