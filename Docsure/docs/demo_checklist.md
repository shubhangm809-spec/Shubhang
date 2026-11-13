# Hackathon Demo Checklist

## Before presenting
- [ ] Start MongoDB / confirm Atlas connection.
- [ ] Start FastAPI and check `/api/health`.
- [ ] Start React with `npm run dev`.
- [ ] Upload 3–5 dummy sample documents: invoice, purchase order, contract and licence.
- [ ] For OCR demo, use a clear high-resolution image and confirm Tesseract is installed.
- [ ] Verify suggested category and expiry date manually.
- [ ] Keep a backup screenshot/video in case Wi-Fi or database access fails.
- [ ] Never demo real confidential customer or identity documents.

## Suggested 3-minute demo
1. 30 sec — Explain SME problem and solution.
2. 45 sec — Upload sample invoice and show extracted text/category.
3. 30 sec — Show document list and search.
4. 30 sec — Show expiry alert and verify an expiry date.
5. 30 sec — Explain React, FastAPI, MongoDB and OCR architecture.
6. 15 sec — State limitations and future scope.

## Troubleshooting
- Backend not reachable: check terminal, port 8000 and CORS origin.
- MongoDB unavailable: check `MONGODB_URI`, database user/password and Atlas IP allowlist.
- Empty scanned PDF extraction: install Tesseract and add it to PATH.
- Frontend dependencies: run `npm install` inside `frontend`.
