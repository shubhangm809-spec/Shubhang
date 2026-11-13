# DOCUSURE — SME Compliance & Document Intelligence

A hackathon-ready MVP using React + Vite, Python FastAPI, MongoDB, PyMuPDF and Tesseract OCR.

## Features
- Upload PDF, PNG and JPG documents
- Extract PDF text with PyMuPDF; image/scanned-PDF OCR with Tesseract when installed
- Rule-based document categorisation
- Extract likely dates and suggest an expiry date
- Dashboard counts and upcoming/expired alerts
- Search by document name, category or extracted text
- View extracted text and edit/confirm metadata

> This is a prototype, not legal advice. OCR and date/category extraction are suggestions and must be verified by a person.

## Requirements
- Python 3.10+
- Node.js 18+
- MongoDB local or MongoDB Atlas connection string
- Optional: Tesseract OCR installed and available on PATH for scanned images/PDFs

## 1. Backend setup (VS Code terminal)
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
# .venv\Scripts\activate.bat
pip install -r requirements.txt
copy .env.example .env
```
Edit `backend/.env` and set `MONGODB_URI` to your MongoDB connection string.

Start the backend:
```bash
uvicorn app.main:app --reload --port 8000
```
API docs: http://127.0.0.1:8000/docs

## 2. Frontend setup (second VS Code terminal)
```bash
cd frontend
npm install
npm run dev
```
Open the URL printed by Vite, usually http://localhost:5173.

## MongoDB Atlas quick setup
1. Create a free cluster at https://www.mongodb.com/atlas.
2. Create a database user and password.
3. In Network Access, allow your current IP for development.
4. Copy the Python driver connection string.
5. Put it in `backend/.env` as `MONGODB_URI`.
6. Never publish your real connection string or API keys in GitHub.

## OCR notes
- Digital PDFs are read directly.
- For scanned PDFs, the app attempts OCR if Tesseract is installed.
- For PNG/JPG, the app attempts OCR.
- If Tesseract is missing, the upload is still stored, but extraction may be empty. Install Tesseract and add it to PATH to enable OCR.

## Demo flow for judges
1. Open dashboard and explain the compliance overview.
2. Upload a sample invoice PDF or licence image.
3. Show the detected category and extracted text.
4. Confirm/edit the suggested expiry date.
5. Show the upcoming/expired alert.
6. Search for a phrase or document category.

## Suggested sample documents
Use dummy/sample documents only. Do not upload confidential business, personal, banking or government identity documents during a public hackathon demo.

## API endpoints
- `GET /api/health`
- `GET /api/dashboard`
- `POST /api/documents` (multipart field `file`)
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `PATCH /api/documents/{document_id}`
- `DELETE /api/documents/{document_id}`
- `GET /api/alerts`
- `GET /api/search?q=...`

## Folder structure
```text
docusure_hackathon/
  backend/
    app/main.py
    app/services/intelligence.py
    requirements.txt
    .env.example
  frontend/
    index.html
    package.json
    vite.config.js
    src/
      main.jsx
      App.jsx
      styles.css
  docs/
    architecture.md
    judge_document.md
    pitch_script.md
    demo_checklist.md
```
