"""
KrishiMandal Serverless — Learning Platform Lambda
Delivers personalised learning content with S3 presigned URLs.
"""
import json
import logging

import boto3

from common.config import config
from common.fallback import fallback_to_ec2
from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=config.AWS_REGION)
    return _s3_client


def _presigned_url(key: str, expires: int = 3600) -> str:
    """Generate a presigned URL for an S3 object."""
    return _get_s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": config.S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )


# Learning content corpus with S3 keys for HTML guides
LEARNING_CONTENT = [
    {
        "content_id": "LC001",
        "title": "Integrated Pest Management (IPM) for Kharif Crops",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "pest_control",
        "s3_key": "learning/ipm_kharif_crops.html",
        "duration_minutes": 12,
        "relevance_score": 0.92,
    },
    {
        "content_id": "LC002",
        "title": "Zero Budget Natural Farming — Subhash Palekar Method",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "organic_farming",
        "s3_key": "learning/zero_budget_farming.html",
        "duration_minutes": 18,
        "relevance_score": 0.88,
    },
    {
        "content_id": "LC003",
        "title": "Drip Irrigation Setup Guide for Small Farms",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "drip_irrigation",
        "s3_key": "learning/drip_irrigation_guide.html",
        "duration_minutes": 8,
        "relevance_score": 0.85,
    },
    {
        "content_id": "LC004",
        "title": "Soil Health Card — How to Read and Act",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "soil_health",
        "s3_key": "learning/soil_health_card.html",
        "duration_minutes": 10,
        "relevance_score": 0.90,
    },
    {
        "content_id": "LC005",
        "title": "Rainwater Harvesting — Farm Pond Construction",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "water_management",
        "s3_key": "learning/rainwater_harvesting.html",
        "duration_minutes": 15,
        "relevance_score": 0.87,
    },
    {
        "content_id": "LC006",
        "title": "PM-KISAN Registration Step-by-Step",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "pm_kisan",
        "s3_key": "learning/pm_kisan_guide.html",
        "duration_minutes": 5,
        "relevance_score": 0.93,
    },
    {
        "content_id": "LC007",
        "title": "PMFBY Crop Insurance — How to Claim",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "pmfby",
        "s3_key": "learning/pmfby_insurance.html",
        "duration_minutes": 7,
        "relevance_score": 0.86,
    },
    {
        "content_id": "LC008",
        "title": "Vermicompost Production at Home",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "organic_farming",
        "s3_key": "learning/vermicompost_guide.html",
        "duration_minutes": 14,
        "relevance_score": 0.84,
    },
    {
        "content_id": "LC009",
        "title": "Neem-based Bio-Pesticide Preparation",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "pest_control",
        "s3_key": "learning/neem_biopesticide.html",
        "duration_minutes": 9,
        "relevance_score": 0.89,
    },
    {
        "content_id": "LC010",
        "title": "Micro-Irrigation Subsidy — Application Guide",
        "content_type": "article",
        "language": "hi-IN",
        "topic": "drip_irrigation",
        "s3_key": "learning/micro_irrigation_subsidy.html",
        "duration_minutes": 6,
        "relevance_score": 0.91,
    },
]


def handler(event, context):
    """Lambda handler for GET /learning/content."""
    try:
        method = event.get("httpMethod", "GET")
        qs = event.get("queryStringParameters") or {}

        if method != "GET":
            return bad_request("Only GET is supported.")

        topic = qs.get("topic")

        content = LEARNING_CONTENT[:]

        # Filter by topic
        if topic:
            content = [c for c in content if c["topic"] == topic]

        # Sort by relevance
        content.sort(key=lambda c: c["relevance_score"], reverse=True)

        # Generate presigned URLs for each item
        result = []
        for item in content:
            entry = {**item}
            try:
                entry["url"] = _presigned_url(item["s3_key"])
            except Exception:
                entry["url"] = "#"
            # Remove internal s3_key from response
            entry.pop("s3_key", None)
            result.append(entry)

        return ok(result)

    except Exception as e:
        logger.error("Learning handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(method="GET", path=event.get("path", "/learning/content"))
        return fb or error(str(e))
