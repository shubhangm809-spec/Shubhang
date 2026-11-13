
# Agentic AI Server

A local Agentic AI application built using Python, FastAPI, Ollama, and ChromaDB.

## Features

- AI chat using Qwen 2.5 3B
- Agent tool execution
- Web search and page fetching
- PDF upload and processing
- Document retrieval using ChromaDB
- API-key authentication
- 10 MB PDF upload limit
- Query logging
- Browser-based chat interface

## Technologies

- Python 3.12
- FastAPI
- Ollama
- Qwen 2.5 3B
- ChromaDB
- nomic-embed-text
- Uvicorn

## Installation

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Start Ollama

Make sure Ollama is installed and the required models are available:

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

## Start the server

```bash
uvicorn main:app --reload --port 8000
```

## Open the application

API documentation:

http://127.0.0.1:8000/docs

Web interface:

http://127.0.0.1:8000/ui/

## API authentication

Protected endpoints require this header:

```text
x-api-key: your-api-key
```

For local testing, the default key is:

```text
my-secret-key-123
```

Set a secure API_KEY environment variable before deployment.

## Project structure

```text
ai-server/
├── main.py
├── agent.py
├── tools.py
├── rag.py
├── requirements.txt
├── static/
│   └── index.html
├── uploaded_documents/
├── logs/
└── chroma_db/
```
