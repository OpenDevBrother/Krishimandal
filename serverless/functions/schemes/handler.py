"""
KrishiMandal Serverless — Schemes Lambda
Government scheme matching and listing.
"""
import json
import logging

from common.dynamo_repository import get_repository
from common.fallback import fallback_to_ec2
from common.response import ok, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Default schemes to seed if none exist
DEFAULT_SCHEMES = [
    {"id": "PMKISAN", "name": "PM-KISAN Samman Nidhi", "benefits_inr": 6000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record", "Bank Passbook"], "eligibility": {"max_area_hectares": 5}},
    {"id": "PMFBY", "name": "PM Fasal Bima Yojana", "benefits_inr": 25000, "deadline": "2026-06-30",
     "requirements": ["Aadhaar", "Land Record", "Crop Sowing Certificate"], "eligibility": {"min_area_hectares": 0.5}},
    {"id": "PMKUSUM", "name": "PM-KUSUM Solar Pump", "benefits_inr": 50000, "deadline": "2026-09-30",
     "requirements": ["Aadhaar", "Land Record", "Electricity Bill"], "eligibility": {}},
    {"id": "SHC", "name": "Soil Health Card Scheme", "benefits_inr": 0, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record"], "eligibility": {}},
    {"id": "KCC", "name": "Kisan Credit Card", "benefits_inr": 300000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record", "Bank Passbook", "Income Certificate"], "eligibility": {}},
    {"id": "MKSP", "name": "Mahila Kisan Sashaktikaran Pariyojana", "benefits_inr": 15000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record"], "eligibility": {"gender": "female"}},
    {"id": "NMSA", "name": "National Mission for Sustainable Agriculture", "benefits_inr": 20000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record"], "eligibility": {}},
    {"id": "RKVY", "name": "Rashtriya Krishi Vikas Yojana", "benefits_inr": 10000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record"], "eligibility": {}},
    {"id": "BKSY", "name": "Bhagyalaxmi Krishi Sinchan Yojana (MH)", "benefits_inr": 30000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record", "Domicile Certificate"], "eligibility": {"state": "Maharashtra"}},
    {"id": "SJSY", "name": "Shetkari Jansuraksha Yojana (MH)", "benefits_inr": 200000, "deadline": "2026-12-31",
     "requirements": ["Aadhaar", "Land Record"], "eligibility": {"state": "Maharashtra"}},
]


def handler(event, context):
    """Lambda handler for /schemes endpoints."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        repo = get_repository()

        # GET /schemes — list all schemes
        if method == "GET":
            schemes = repo.get_schemes()
            if not schemes:
                # Seed default schemes
                for s in DEFAULT_SCHEMES:
                    repo.save_scheme(s["id"], s)
                schemes = repo.get_schemes()

            # Clean DynamoDB keys from response
            result = []
            for s in schemes:
                clean = {k: v for k, v in s.items() if k not in ("PK", "SK", "entity_type")}
                result.append(clean)

            return ok(result)

        return ok([])

    except Exception as e:
        logger.error("Schemes handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(method="GET", path="/schemes")
        return fb or error(str(e))
