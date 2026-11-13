
import chromadb
import httpx
from pypdf import PdfReader


# 1. CHROMADB CONFIGURATION

client = chromadb.PersistentClient(path="./chroma_db")

_collection = client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)


# 2. OLLAMA EMBEDDING FUNCTION

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"


def create_embedding(text):

    response = httpx.post(
        OLLAMA_URL,
        json={
            "model": EMBED_MODEL,
            "input": text
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["embeddings"][0]


# 3. TEXT CHUNKING FUNCTION

def split_text(text, chunk_size=800, overlap=150):

    chunks = []
    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# 4. PDF PROCESSING FUNCTION

def process_pdf(file_path, filename):

    reader = PdfReader(file_path)

    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for page_number, page in enumerate(reader.pages, start=1):

        page_text = page.extract_text() or ""

        chunks = split_text(page_text)

        for chunk_number, chunk in enumerate(chunks):

            embedding = create_embedding(chunk)

            document_id = f"{filename}_page{page_number}_chunk{chunk_number}"

            ids.append(document_id)
            documents.append(chunk)
            embeddings.append(embedding)

            metadatas.append({
                "filename": filename,
                "page": page_number
            })

    if ids:

        _collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    return {
        "filename": filename,
        "pages": len(reader.pages),
        "chunks": len(ids),
        "message": "PDF processed successfully"
    }


# 5. DOCUMENT SEARCH FUNCTION

def search_documents(query, n_results=3):

    count = _collection.count()

    if count == 0:
        return []

    query_embedding = create_embedding(query)

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, count)
    )

    search_results = []

    for i in range(len(results["documents"][0])):

        search_results.append({
            "text": results["documents"][0][i],
            "filename": results["metadatas"][0][i]["filename"],
            "page": results["metadatas"][0][i]["page"],
            "distance": results["distances"][0][i]
        })

    return search_results


# 6. LIST UPLOADED DOCUMENTS

def list_documents():

    results = _collection.get(
        include=["metadatas"]
    )

    documents = {}

    for metadata in results["metadatas"]:

        filename = metadata["filename"]
        documents[filename] = True

    return sorted(documents.keys())
