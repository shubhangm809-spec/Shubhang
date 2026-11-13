
import os
import re
import io
import statistics
from pathlib import Path
from collections import Counter
from datetime import date

import fitz
import pytesseract
import numpy as np
import cv2

from PIL import Image
from dateutil import parser as date_parser


# ============================================================
# CONFIGURATION
# ============================================================

TESSERACT_PATH = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
OCR_CONFIGS = [
    "--oem 3 --psm 6",
    "--oem 3 --psm 4",
    "--oem 3 --psm 11",
]

MIN_PDF_TEXT_LENGTH = 40
MAX_IMAGE_PIXELS = 25_000_000


# ============================================================
# DOCUMENT CLASSIFICATION
# ============================================================

CATEGORY_KEYWORDS = {
    "Aadhaar": [
        "aadhaar", "aadhar", "uidai",
        "unique identification authority"
    ],
    "PAN Card": [
        "permanent account number",
        "income tax department", "pan card"
    ],
    "Passport": [
        "passport", "place of birth",
        "passport no", "republic of india"
    ],
    "Voter ID": [
        "election commission",
        "elector photo identity card", "epic number"
    ],
    "Driving Licence": [
        "driving licence", "driving license",
        "licence no", "transport department"
    ],
    "Vehicle Registration": [
        "registration certificate", "registered owner",
        "chassis number", "vehicle class"
    ],
    "Insurance": [
        "insurance policy", "policy number",
        "sum insured", "premium"
    ],
    "PUC Certificate": [
        "pollution under control", "puc certificate",
        "emission test"
    ],
    "GST Document": [
        "goods and services tax", "gstin",
        "gst registration"
    ],
    "Invoice": [
        "invoice", "tax invoice", "invoice number",
        "amount payable"
    ],
    "Purchase Order": [
        "purchase order", "po number",
        "order quantity"
    ],
    "Contract": [
        "agreement", "contract",
        "terms and conditions"
    ],
    "Licence": [
        "licence", "license",
        "licensing authority", "permit number"
    ],
    "Certificate": [
        "certificate", "certified that",
        "this is to certify"
    ],
    "Education": [
        "marks card", "mark sheet", "marksheet",
        "university", "degree certificate",
        "academic transcript"
    ],
    "Bank Statement": [
        "bank statement", "account statement",
        "opening balance", "closing balance",
        "transaction date", "ifsc",
        "account holder", "available balance",
        "withdrawal", "deposit"
    ],
}


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):
    """
    Produce an enhanced image for OCR.

    Uses grayscale, denoising, local contrast enhancement
    and adaptive thresholding.

    Returns a PIL image.
    """

    if image.width * image.height > MAX_IMAGE_PIXELS:
        image.thumbnail((5000, 5000))

    rgb = image.convert("RGB")

    array = np.array(rgb)
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)

    # Improve resolution for small documents.
    height, width = gray.shape

    if width < 1800:
        scale = min(1800 / width, 2.0)

        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # Remove camera noise.
    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        h=10,
        templateWindowSize=7,
        searchWindowSize=21
    )

    # Improve local contrast in poor lighting.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(denoised)

    # Sharpen slightly.
    blurred = cv2.GaussianBlur(
        enhanced,
        (0, 0),
        1.0
    )

    sharpened = cv2.addWeighted(
        enhanced,
        1.5,
        blurred,
        -0.5,
        0
    )

    # Adaptive thresholding.
    threshold = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    return Image.fromarray(threshold)


def image_quality(image):
    """
    Estimate image quality.

    This is a diagnostic score, not an OCR accuracy score.
    """

    gray = cv2.cvtColor(
        np.array(image.convert("RGB")),
        cv2.COLOR_RGB2GRAY
    )

    blur_value = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    return {
        "blur_score": round(float(blur_value), 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "low_light": brightness < 65,
        "possible_blur": blur_value < 45,
        "low_contrast": contrast < 30
    }


# ============================================================
# OCR ENGINE
# ============================================================

def run_ocr(image):
    """
    Run multiple Tesseract page segmentation modes.

    Select the result with the highest average recognized
    word confidence, while retaining the text and confidence.
    """

    best = {
        "text": "",
        "confidence": 0.0,
        "word_count": 0
    }

    for config in OCR_CONFIGS:

        try:
            data = pytesseract.image_to_data(
                image,
                lang=OCR_LANGUAGE,
                config=config,
                output_type=pytesseract.Output.DICT
            )

            words = []
            confidences = []

            for index, word in enumerate(data["text"]):

                word = word.strip()

                try:
                    confidence = float(
                        data["conf"][index]
                    )
                except (ValueError, TypeError):
                    continue

                if word and confidence >= 0:
                    words.append(word)
                    confidences.append(confidence)

            text = " ".join(words)

            average = (
                sum(confidences) / len(confidences)
                if confidences else 0
            )

            if average > best["confidence"]:
                best = {
                    "text": text,
                    "confidence": round(average / 100, 3),
                    "word_count": len(words)
                }

        except Exception as error:
            print("OCR configuration error:", error)

    return best


def extract_image_result(image_path):
    """
    Extract text and diagnostics from an image.
    """

    with Image.open(image_path) as source:

        source = source.convert("RGB")

        quality = image_quality(source)
        enhanced = preprocess_image(source)

        result = run_ocr(enhanced)

        # If preprocessing gives little usable text,
        # try OCR on the original image as a fallback.
        if result["word_count"] < 5:

            original_result = run_ocr(source)

            if original_result["word_count"] > result["word_count"]:
                result = original_result

        result["quality"] = quality

        return result


def extract_image_text(image_path):
    try:
        return clean_text(
            extract_image_result(image_path)["text"]
        )

    except Exception as error:
        print("Image OCR error:", error)
        return ""


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_result(pdf_path):
    pages = []
    quality_results = []

    try:
        with fitz.open(pdf_path) as pdf:

            for page in pdf:

                # First use embedded PDF text.
                embedded = page.get_text("text").strip()

                if len(embedded) >= MIN_PDF_TEXT_LENGTH:

                    pages.append(embedded)

                    quality_results.append({
                        "source": "embedded_pdf_text",
                        "confidence": 1.0
                    })

                    continue

                # Render scanned page at approximately 300 DPI.
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(300 / 72, 300 / 72),
                    alpha=False
                )

                image = Image.open(
                    io.BytesIO(pix.tobytes("png"))
                ).convert("RGB")

                quality = image_quality(image)
                enhanced = preprocess_image(image)

                result = run_ocr(enhanced)

                if result["word_count"] < 5:

                    original_result = run_ocr(image)

                    if original_result["word_count"] > result["word_count"]:
                        result = original_result

                pages.append(result["text"])

                quality_results.append({
                    "source": "tesseract_ocr",
                    "confidence": result["confidence"],
                    "quality": quality
                })

    except Exception as error:
        print("PDF extraction error:", error)

    return {
        "text": clean_text("\n".join(pages)),
        "pages": quality_results
    }


def extract_pdf_text(pdf_path):
    return extract_pdf_result(pdf_path)["text"]


# ============================================================
# MAIN TEXT EXTRACTION
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


def extract_text_from_file(file_path):

    if not file_path or not os.path.exists(file_path):
        return ""

    extension = Path(file_path).suffix.lower()

    try:
        if extension == ".pdf":
            return extract_pdf_text(file_path)

        if extension in {".jpg", ".jpeg", ".png"}:
            return extract_image_text(file_path)

    except Exception as error:
        print("Document extraction error:", error)

    return ""


def extract_ocr_details(file_path):
    """
    Return text plus OCR diagnostic information.
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        result = extract_pdf_result(file_path)

        confidences = [
            page["confidence"]
            for page in result["pages"]
            if "confidence" in page
        ]

        return {
            "text": result["text"],
            "ocr_confidence": (
                round(sum(confidences) / len(confidences), 3)
                if confidences else 0
            ),
            "pages": result["pages"]
        }

    if extension in {".jpg", ".jpeg", ".png"}:
        result = extract_image_result(file_path)

        return {
            "text": clean_text(result["text"]),
            "ocr_confidence": result["confidence"],
            "quality": result["quality"]
        }

    return {
        "text": "",
        "ocr_confidence": 0
    }


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_document(text, filename=""):

    content = (text or "").lower()
    filename_text = (filename or "").lower()

    scores = Counter()

    for category, keywords in CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            occurrences = content.count(keyword.lower())

            if occurrences:
                scores[category] += occurrences * 2

            if keyword.lower() in filename_text:
                scores[category] += 0.5

    if not scores:
        return "Other", 0.0

    ranked = scores.most_common()

    best_category, best_score = ranked[0]
    total_score = sum(scores.values())

    confidence = best_score / total_score if total_score else 0

    evidence_count = sum(
        1
        for keywords in CATEGORY_KEYWORDS.values()
        for keyword in keywords
        if keyword.lower() in content
    )

    if evidence_count == 1:
        confidence = min(confidence, 0.50)

    return best_category, round(min(confidence, 0.99), 2)


# ============================================================
# DATE EXTRACTION
# ============================================================

DATE_PATTERN = re.compile(
    r"\b(?:"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|"
    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"
    r"|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}"
    r"|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}"
    r")\b",
    re.IGNORECASE
)


def parse_date_value(value):

    try:
        parsed = date_parser.parse(
            value,
            dayfirst=True,
            fuzzy=False
        )

        if parsed.year < 1900 or parsed.year > 2200:
            return None

        return parsed.date()

    except (ValueError, TypeError, OverflowError):
        return None


def extract_dates(text):

    results = []

    for match in DATE_PATTERN.finditer(text or ""):

        parsed = parse_date_value(match.group(0))

        if parsed:
            results.append(parsed.isoformat())

    return sorted(set(results))


# ============================================================
# EXPIRY DATE DETECTION
# ============================================================

EXPIRY_LABELS = [
    "expiry date",
    "expiration date",
    "date of expiry",
    "valid until",
    "valid till",
    "valid upto",
    "valid up to",
    "valid through",
    "validity upto",
    "validity up to",
    "date of validity",
    "validity date",
    "expires on",
    "expiry",
    "expiration"
]


def suggest_expiry_date(text):

    if not text:
        return None

    lines = text.splitlines()

    for index, line in enumerate(lines):

        normalized = line.lower()

        if not any(label in normalized for label in EXPIRY_LABELS):
            continue

        candidates = DATE_PATTERN.findall(line)

        if not candidates and index + 1 < len(lines):
            candidates = DATE_PATTERN.findall(lines[index + 1])

        for value in candidates:

            parsed = parse_date_value(value)

            if parsed:
                return parsed.isoformat()

    return None


# ============================================================
# GENERAL FIELD EXTRACTION
# ============================================================

def extract_fields(text):

    if not text:
        return {}

    fields = {}

    email = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    )

    if email:
        fields["email"] = email.group(0)

    phone = re.search(
        r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",
        text
    )

    if phone:
        fields["phone"] = phone.group(0)

    pan = re.search(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        text.upper()
    )

    if pan:
        value = pan.group(0)
        fields["pan_masked"] = value[:2] + "XXXXXX" + value[-1]

    aadhaar = re.search(
        r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)",
        text
    )

    if aadhaar:
        digits = re.sub(r"\D", "", aadhaar.group(0))
        fields["aadhaar_masked"] = "XXXX-XXXX-" + digits[-4:]

    gst = re.search(
        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b",
        text.upper()
    )

    if gst:
        value = gst.group(0)
        fields["gstin_masked"] = value[:2] + "XXXXXXXXXXXX" + value[-3:]

    amount = re.search(
        r"(?:total amount|grand total|amount payable|net amount|total)"
        r"\s*[:\-]?\s*(?:INR|Rs\.?|₹)?\s*[\d,]+(?:\.\d{1,2})?",
        text,
        re.IGNORECASE
    )

    if amount:
        fields["amount_text"] = amount.group(0).strip()

    return fields


# ============================================================
# BANK DOCUMENT EXTRACTION
# ============================================================

BANK_NAMES = [
    "State Bank of India",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Kotak Mahindra Bank",
    "Bank of Baroda",
    "Punjab National Bank",
    "Canara Bank",
    "Union Bank of India",
    "Indian Bank",
    "Bank of India",
    "IDFC FIRST Bank",
    "IndusInd Bank",
    "Federal Bank",
    "Yes Bank",
    "Karnataka Bank",
    "Central Bank of India"
]


def find_labeled_value(text, labels):
    """
    Find text following a field label.
    Returns a candidate only; it is not guaranteed correct.
    """

    lines = text.splitlines()

    for index, line in enumerate(lines):

        lower = line.lower()

        for label in labels:

            position = lower.find(label.lower())

            if position < 0:
                continue

            value = line[position + len(label):]

            value = re.sub(
                r"^[\s:#=\-]+",
                "",
                value
            ).strip()

            if value and len(value) <= 100:
                return value

            if index + 1 < len(lines):

                next_line = lines[index + 1].strip()

                if next_line and len(next_line) <= 100:
                    return next_line

    return None


def extract_bank_fields(text):

    if not text:
        return {}

    fields = {}
    normalized = text.lower()

    # Bank name.
    for bank in BANK_NAMES:

        if bank.lower() in normalized:
            fields["bank_name"] = bank
            break

    # IFSC code.
    ifsc_match = re.search(
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        text.upper()
    )

    if ifsc_match:
        fields["ifsc"] = ifsc_match.group(0)

    # MICR code.
    micr_match = re.search(
        r"(?<!\d)\d{9}(?!\d)",
        text
    )

    if micr_match:
        fields["micr_candidate"] = micr_match.group(0)

    # Account number: require a nearby account label.
    account_value = find_labeled_value(
        text,
        [
            "account number",
            "account no",
            "a/c number",
            "a/c no",
            "ac number",
            "ac no"
        ]
    )

    if account_value:

        account_digits = re.sub(
            r"\D",
            "",
            account_value
        )

        if 6 <= len(account_digits) <= 20:

            fields["account_number_masked"] = (
                "X" * (len(account_digits) - 4)
                + account_digits[-4:]
            )

            fields["account_number_review_required"] = True

    # Account holder.
    holder = find_labeled_value(
        text,
        [
            "account holder",
            "account name",
            "customer name",
            "name of account holder"
        ]
    )

    if holder:
        fields["account_holder_candidate"] = holder[:100]

    # Branch.
    branch = find_labeled_value(
        text,
        ["branch name", "branch"]
    )

    if branch:
        fields["branch_candidate"] = branch[:100]

    # Account type.
    account_type = re.search(
        r"\b(savings|current|salary)\s+account\b",
        text,
        re.IGNORECASE
    )

    if account_type:
        fields["account_type"] = account_type.group(0).title()

    # Statement period.
    period = re.search(
        r"(?:statement period|period)\s*[:\-]?\s*"
        r"(.{1,80})",
        text,
        re.IGNORECASE
    )

    if period:
        fields["statement_period_candidate"] = period.group(1).strip()

    # Opening and closing balances.
    amount_pattern = (
        r"(?:INR|Rs\.?|₹)?\s*"
        r"([\d,]+(?:\.\d{1,2})?)"
    )

    for field_name, labels in {
        "opening_balance_candidate": [
            "opening balance",
            "balance brought forward"
        ],
        "closing_balance_candidate": [
            "closing balance",
            "ending balance"
        ]
    }.items():

        for label in labels:

            match = re.search(
                re.escape(label) + r"\s*[:\-]?\s*" + amount_pattern,
                text,
                re.IGNORECASE
            )

            if match:
                fields[field_name] = match.group(1)
                break

    return fields


# ============================================================
# BASIC TRANSACTION ROW EXTRACTION
# ============================================================

def extract_transaction_candidates(text):
    """
    Extract candidate transaction lines.

    This deliberately does not pretend that plain OCR text
    reliably preserves every bank's table columns.
    """

    transactions = []

    if not text:
        return transactions

    lines = text.splitlines()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        date_match = DATE_PATTERN.search(line)

        if not date_match:
            continue

        amounts = re.findall(
            r"(?<![A-Za-z])(?:\d{1,3}(?:,\d{2,3})+|\d+)"
            r"(?:\.\d{2})?",
            line
        )

        if not amounts:
            continue

        transactions.append({
            "date_candidate": date_match.group(0),
            "line_candidate": line[:300],
            "amount_candidates": amounts,
            "review_required": True
        })

    return transactions[:500]


# ============================================================
# COMPLETE DOCUMENT ANALYSIS
# ============================================================

def analyze_document(file_path, filename=None):

    filename = filename or os.path.basename(file_path)

    ocr = extract_ocr_details(file_path)

    extracted_text = ocr["text"]

    category, confidence = classify_document(
        extracted_text,
        filename
    )

    dates = extract_dates(extracted_text)

    expiry_date = suggest_expiry_date(extracted_text)

    fields = extract_fields(extracted_text)

    bank_fields = {}

    transactions = []

    if category == "Bank Statement":
        bank_fields = extract_bank_fields(extracted_text)
        transactions = extract_transaction_candidates(extracted_text)

    quality = ocr.get("quality", {})

    review_required = (
        not extracted_text
        or category == "Other"
        or confidence < 0.50
        or ocr.get("ocr_confidence", 0) < 0.70
        or bool(bank_fields)
    )

    return {
        "filename": filename,
        "category": category,
        "confidence": confidence,
        "extracted_text": extracted_text[:50000],
        "dates_found": dates,
        "expiry_date": expiry_date,
        "extracted_fields": fields,
        "bank_fields": bank_fields,
        "transaction_candidates": transactions,
        "ocr_confidence": ocr.get("ocr_confidence", 0),
        "image_quality": quality,
        "ocr_pages": ocr.get("pages", []),
        "review_required": review_required,
        "ocr_success": bool(extracted_text)
    }
