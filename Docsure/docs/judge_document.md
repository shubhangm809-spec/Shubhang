# DOCUSURE — Project Documentation for Judges

## 1. Title
DOCUSURE: SME Compliance & Document Intelligence Platform

## 2. Problem statement
Small and medium-sized enterprises manage invoices, purchase orders, contracts, licences and certificates manually. This makes it difficult to locate information, identify document types and track important renewal or expiry dates. Missed deadlines can cause operational disruption, penalties or business risk.

## 3. Proposed solution
DOCUSURE is a web-based document intelligence prototype. It accepts business documents, extracts text, suggests a document category, identifies dates, highlights possible expiry risks and makes documents searchable from one workspace.

## 4. Objectives
1. Reduce manual document sorting.
2. Make important document information easier to find.
3. Identify possible expiry dates and display reminders.
4. Provide a central document library.
5. Demonstrate full-stack integration using React, Python REST APIs and MongoDB.

## 5. Technologies
- React.js: component-based user interface.
- HTML, CSS and JavaScript: presentation and client-side behaviour.
- Python FastAPI: backend and REST API.
- MongoDB: document metadata storage.
- PyMuPDF: PDF text extraction.
- Tesseract OCR: optional text extraction from scanned images/PDFs.

## 6. Modules
- Dashboard: document totals, categories and alert counts.
- Upload: validates and accepts PDF/JPG/PNG files.
- Extraction: extracts text from supported documents.
- Classification: keyword-based category suggestion.
- Date detection: detects common date formats and suggests expiry dates when labelled.
- Expiry monitoring: shows expired and next-30-day documents.
- Search: finds documents by filename, category or extracted text.
- Review: allows a human to confirm the expiry date and open the source file.

## 7. System workflow
Upload → Validate → Extract text/OCR → Categorise → Detect dates → Store metadata in MongoDB → Dashboard/Search/Alerts → Human verification.

## 8. Expected outcome
A business user can upload a sample document, see extracted text and a suggested category, review date information, and find documents or expiry alerts through a single web interface.

## 9. Novelty / value
The prototype combines document storage with an intelligence workflow: extraction, classification, date detection, expiry monitoring and search. It is designed around the practical needs of SMEs rather than being only a generic file upload system.

## 10. Limitations
The current MVP uses explainable keyword rules and pattern-based date extraction. OCR results depend on image quality. It does not certify legal compliance and cannot guarantee that every expiry date is detected. Human review is required.

## 11. Future scope
- User authentication and employee/admin roles.
- Email/WhatsApp reminders.
- Multilingual OCR.
- ML-based document classification.
- Semantic search with page-level citations.
- Audit trail, encryption, access control and cloud deployment.
- Integration with accounting and enterprise resource planning systems.

## 12. Conclusion
DOCUSURE demonstrates how full-stack web development and document processing can help SMEs organise business records and become more proactive about important deadlines.
