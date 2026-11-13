# DOCUSURE — Hackathon Pitch Script

## 60–90 second opening
Good morning respected judges.

Our project is **DOCUSURE — SME Compliance and Document Intelligence**.

Small and medium-sized businesses handle many important documents such as invoices, purchase orders, contracts, licences and certificates. Often, these documents are stored in different folders and checked manually. Finding information takes time, and an important renewal or expiry date can easily be missed.

To address this problem, we developed DOCUSURE, a centralised document intelligence platform.

A user can upload a PDF or image. Our Python backend extracts the text using PDF text extraction and OCR. It then suggests the document category and identifies dates. The information is stored in MongoDB and displayed through our React dashboard.

The dashboard provides document statistics, searchable records and alerts for expired or soon-to-expire documents. Users can also review and correct the extracted details, because automated extraction must always be verified.

Our goal is simple: help SMEs spend less time organising documents and more time running their business.

Thank you.

## 2-minute technical explanation
We selected React.js for the frontend because it supports reusable components and responsive user interfaces. Python FastAPI provides REST endpoints for document upload, processing, searching and updating. MongoDB stores the document metadata and extracted text.

The workflow begins when a user uploads a PDF, JPG or PNG. The backend validates the file, extracts text using PyMuPDF or Tesseract OCR, and applies transparent keyword rules to suggest a category. It detects common date formats and only proposes an expiry date when it finds nearby expiry-related wording. The result is stored in MongoDB.

The React dashboard consumes the REST APIs and displays recent documents, category statistics and expiry alerts. A user can open a record, inspect the extracted text and confirm or correct the expiry date.

This is an MVP. In a production system, we would add authentication, role-based permissions, stronger OCR, background processing, audit logs, secure file storage and notification integrations.

## Demo narration
1. “This is the Docusure overview dashboard. It gives the business a quick view of its document library and pending expiry risks.”
2. “I will upload a sample document. The backend validates it and extracts text.”
3. “The system suggests a category and displays the dates it found.”
4. “The user can verify the expiry date instead of blindly trusting automated extraction.”
5. “The alert screen highlights documents that are already expired or due within 30 days.”
6. “Finally, the search feature helps locate documents by name, category or extracted words.”

## Questions judges may ask

**Q: Is this a MERN application?**  
A: The frontend and database follow the React and MongoDB parts of the MERN approach, but we use Python FastAPI instead of Node.js/Express for the backend, as required by our project choice. It is a React–Python–MongoDB full-stack application.

**Q: Is the classification AI?**  
A: In this MVP it is explainable keyword-based classification, not a trained machine-learning model. This gives us a transparent baseline. A future version can use a trained classifier or an LLM with evidence-grounded extraction.

**Q: How do you avoid incorrect expiry alerts?**  
A: The system labels extracted details as suggestions. It only proposes an expiry date when expiry-related wording is near a detected date, and the user must verify it.

**Q: Why MongoDB?**  
A: Document metadata and extracted text can vary by document type. MongoDB's flexible document structure is convenient for this prototype.

**Q: What happens if OCR fails?**  
A: The file can still be stored, but the user sees that no text was extracted. Better scan quality and Tesseract installation improve OCR.

**Q: What is the main benefit to SMEs?**  
A: Centralised records, faster retrieval and visibility of important document deadlines.

**Q: What would you improve next?**  
A: Secure login, roles, audit logs, reminder notifications, better OCR, semantic search with source citations and cloud deployment.
