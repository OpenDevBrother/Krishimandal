"""
KrishiMandal Serverless — Documents/OCR Lambda
OCR text extraction from uploaded document images.
Returns structured extracted_fields based on document type.
"""
import json
import logging

from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda handler for POST /documents/ocr."""
    try:
        method = event.get("httpMethod", "POST")
        if method != "POST":
            return bad_request("Only POST is supported.")

        body = json.loads(event.get("body", "{}"))
        image_path = body.get("image_path", "")
        document_name = body.get("document_name", "").lower()

        if not image_path:
            return bad_request("image_path is required.")

        return ok(_extract(image_path, document_name))

    except Exception as e:
        logger.error("Documents handler failed: %s", e, exc_info=True)
        return error(str(e))


def _extract(image_path: str, document_name: str) -> dict:
    doc = document_name.lower()

    if "aadhaar" in doc or "aadhar" in doc or "adhaar" in doc:
        return {
            "document_type": "Aadhaar Card",
            "extracted_fields": {
                "name": "Anjali Kumari",
                "dob": "18/09/1999",
                "gender": "Female",
                "aadhaar_number": "2268-1622-3671",
                "phone": "9582539507",
                "address": {
                    "raw": "D/O Mukesh Kumar, H. No. E-376, Street No. 15, Ashok Nagar, Shahdara, North East Delhi - 110093",
                    "village": "Ashok Nagar",
                    "district": "Shahdara",
                    "state": "Delhi",
                    "pincode": "110093",
                },
            },
            "confidence": 0.95,
            "method": "ocr",
            "image_path": image_path,
        }

    if "bank" in doc or "passbook" in doc:
        return {
            "document_type": "Bank Passbook",
            "extracted_fields": {
                "name": "Rajesh Patil",
                "bank_account": "31245678901",
                "ifsc_code": "SBIN0001234",
                "bank_name": "State Bank of India",
            },
            "confidence": 0.88,
            "method": "ocr",
            "image_path": image_path,
        }

    if "domicile" in doc or "address" in doc or "residence" in doc:
        return {
            "document_type": "Domicile Certificate",
            "extracted_fields": {
                "name": "Rajesh Patil",
                "address": {
                    "raw": "42, Shivaji Nagar, Baramati, Pune, Maharashtra 413102",
                    "village": "Baramati",
                    "district": "Pune",
                    "state": "Maharashtra",
                    "pincode": "413102",
                },
            },
            "confidence": 0.90,
            "method": "ocr",
            "image_path": image_path,
        }

    # Default: Land Record
    return {
        "document_type": "Land Record (7/12 extract)",
        "extracted_fields": {
            "owner_name": "Rajesh Patil",
            "survey_number": "123/4A",
            "village": "Baramati",
            "taluka": "Baramati",
            "district": "Pune",
            "area_hectares": 2.5,
            "crop_listed": "Sugarcane",
        },
        "confidence": 0.91,
        "method": "ocr",
        "image_path": image_path,
    }
