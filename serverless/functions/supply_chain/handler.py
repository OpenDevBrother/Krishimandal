"""
KrishiMandal Serverless — Supply Chain Lambda
Harvest planning, market selection, transport logistics.
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
    """Lambda handler for /farm/{farmer_id}/harvest-plan endpoint."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        farmer_id = path_params.get("farmer_id", "")
        qs = event.get("queryStringParameters") or {}
        crop = qs.get("crop", "wheat")

        if not farmer_id:
            return bad_request("farmer_id is required.")

        if method == "GET":
            harvest_plan = {
                "farm_id": f"FARM-{farmer_id}",
                "harvest_date": (date.today() + timedelta(days=random.randint(7, 30))).isoformat(),
                "expected_yield_quintals": round(random.uniform(8, 30), 1),
                "quality_grade": random.choice(["A", "B"]),
                "labor_required": random.randint(3, 10),
                "target_markets": random.sample(MAHARASHTRA_MANDIS, k=3),
                "storage_recommendation": random.choice([
                    "Sell immediately — prices are favourable.",
                    "Store for 2 weeks in Solapur cold storage (₹15/qtl/day).",
                    "Consider FPO pooling with nearby farmers for better rate.",
                ]),
                "recommendations": [
                    "Arrange combine harvester 3 days before harvest.",
                    "Ensure gunny bags are clean and dry.",
                    "Get quality grading done at nearest APMC.",
                ],
                "market_options": _generate_market_options(crop),
            }
            return ok(harvest_plan)

        return bad_request("Unsupported method.")

    except Exception as e:
        logger.error("Supply chain handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(method="GET", path=event.get("path", ""))
        return fb or error(str(e))


def _generate_market_options(crop: str):
    """Generate ranked market options."""
    options = []
    for mandi in random.sample(MAHARASHTRA_MANDIS, k=4):
        price = random.uniform(2000, 3500)
        dist = random.uniform(10, 80)
        transport = dist * 3.5
        fee_pct = 1.5
        net = price * 20 - transport - (price * 20 * fee_pct / 100)
        options.append({
            "mandi_name": mandi,
            "distance_km": round(dist, 1),
            "expected_price": round(price, 0),
            "market_fee_pct": fee_pct,
            "net_realization": round(net, 0),
            "payment_reliability": random.choice(["excellent", "good", "average"]),
        })
    return sorted(options, key=lambda x: x["net_realization"], reverse=True)
