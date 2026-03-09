"""
KrishiMandal Serverless — Prices Lambda
Mandi price forecasting and history.
"""
import json
import logging
import random
from datetime import date, timedelta

from common.bedrock_service import get_bedrock_llm
from common.dynamo_repository import get_repository
from common.fallback import fallback_to_ec2
from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAHARASHTRA_MANDIS = [
    "Pune (Gultekdi)", "Nashik", "Nagpur (Kalamna)", "Aurangabad",
    "Solapur", "Kolhapur", "Sangli", "Ahmednagar", "Latur", "Jalgaon",
]


def handler(event, context):
    """Lambda handler for /price/{crop} endpoints."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        crop = path_params.get("crop", "wheat")
        qs = event.get("queryStringParameters") or {}
        mandi = qs.get("mandi")
        repo = get_repository()

        if not crop:
            return bad_request("Crop name is required.")

        # GET /price/{crop}/history
        if method == "GET" and path.endswith("/history"):
            days = int(qs.get("days", "30"))
            # Check DynamoDB for stored prices
            latest = repo.get_latest_price(crop, mandi or "Indore")

            # Generate synthetic history if none exists
            history = []
            base_price = float(latest["price"]) if latest else random.uniform(1800, 3500)
            for i in range(days):
                d = date.today() - timedelta(days=days - i)
                price = base_price * random.uniform(0.95, 1.05)
                history.append({
                    "date": d.isoformat(),
                    "price": round(price, 0),
                    "mandi": mandi or "Indore",
                })

            return ok({
                "crop": crop,
                "mandi": mandi or "Indore",
                "days": days,
                "records": history,
            })

        # GET /price/{crop} — forecast
        if method == "GET":
            mandi_name = mandi or random.choice(MAHARASHTRA_MANDIS)

            # Check DynamoDB for latest price
            latest = repo.get_latest_price(crop, mandi_name)
            base_price = float(latest["price"]) if latest else round(random.uniform(1800, 3500), 0)

            forecast = {
                "crop": crop,
                "mandi": mandi_name,
                "current_price": base_price,
                "forecast_7day": round(base_price * random.uniform(0.97, 1.08), 0),
                "forecast_30day": round(base_price * random.uniform(0.92, 1.15), 0),
                "confidence_lower": round(base_price * 0.9, 0),
                "confidence_upper": round(base_price * 1.12, 0),
                "trend": random.choice(["rising", "falling", "stable"]),
                "factors": [
                    {"factor": "supply", "impact": round(random.uniform(-0.5, 0.5), 2),
                     "explanation": "Regional harvest arrivals are moderate"},
                    {"factor": "demand", "impact": round(random.uniform(0, 0.4), 2),
                     "explanation": "Festival season driving demand"},
                    {"factor": "weather", "impact": round(random.uniform(-0.3, 0.1), 2),
                     "explanation": "Unseasonal rains affecting quality"},
                ],
            }

            return ok(forecast)

        return bad_request("Unsupported method.")

    except Exception as e:
        logger.error("Prices handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(method="GET", path=event.get("path", "/price/wheat"))
        return fb or error(str(e))
