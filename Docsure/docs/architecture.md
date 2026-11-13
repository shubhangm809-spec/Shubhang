# DOCUSURE — Architecture and Technical Design

## Architecture
```text
User
  |
  v
React + Vite UI (localhost:5173)
  | HTTP / JSON / multipart upload
  v
Python FastAPI REST API (localhost:8000)
  |-- Validation and file storage
  |-- PyMuPDF / Tesseract text extraction
  |-- Rule-based category and date suggestions
  |-- Expiry alert and search services
  |
  v
MongoDB database (docusure.documents)
```

## Main data model
A document record contains:
- `_id`: MongoDB ObjectId
- `filename`: original file name
- `stored_name`: random safe storage name
- `category`: detected type
- `confidence`: heuristic confidence score
- `uploaded_at`: UTC upload timestamp
- `expiry_date`: verified or suggested ISO date (`YYYY-MM-DD`)
- `dates_found`: dates detected in text
- `extracted_text`: OCR/PDF text preview
- `notes`: optional user notes
- `status`: review status

## Processing workflow
1. User uploads a PDF or image from React.
2. FastAPI validates extension and file size.
3. The file is stored under a random server-generated name.
4. PyMuPDF extracts text from text-based PDFs.
5. Tesseract attempts OCR for image files or scanned PDFs.
6. Keyword rules suggest a document category.
7. Date patterns are extracted. A date is only suggested as expiry when expiry-related wording is nearby.
8. Metadata is saved in MongoDB.
9. Dashboard, search and alerts query MongoDB.
10. User reviews and confirms important information.

## API design
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API and MongoDB status |
| POST | `/api/documents` | Upload a document |
| GET | `/api/documents` | List/filter documents |
| GET | `/api/documents/{id}` | Read metadata |
| PATCH | `/api/documents/{id}` | Verify/update metadata |
| DELETE | `/api/documents/{id}` | Delete metadata and file |
| GET | `/api/documents/{id}/file` | Open original |
| GET | `/api/dashboard` | Summary counts |
| GET | `/api/alerts` | Expiry alerts |
| GET | `/api/search?q=...` | Search documents |

## Limitations and next improvements
- Current categorisation is explainable keyword matching, not a trained ML model.
- OCR quality depends on scan quality and Tesseract language packs.
- Date extraction supports common numeric and English month formats.
- Production deployment should add login, role-based access, encryption, malware scanning, audit logs, backups, retention policies and private object storage.
- A production version should use background jobs for large files and a robust natural-language retrieval model with citations to page/section locations.
