"""
KrishiMandal Serverless — EventBridge Integration
Replaces in-process pub/sub with AWS EventBridge.
"""
import json
import logging
from typing import Any, Dict

import boto3

from common.config import config

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client("events", region_name=config.AWS_REGION)
    return _client


def publish_event(event_type: str, detail: Dict[str, Any], farmer_id: str = ""):
    """Publish an event to EventBridge."""
    try:
        _get_client().put_events(
            Entries=[{
                "Source": "krishimandal",
                "DetailType": event_type,
                "Detail": json.dumps({
                    "farmer_id": farmer_id,
                    **detail,
                }),
                "EventBusName": config.EVENTS_BUS_NAME,
            }]
        )
        logger.info("Published event: %s for farmer %s", event_type, farmer_id)
    except Exception as e:
        logger.error("Failed to publish event %s: %s", event_type, e)


def event_to_notification(event_type: str, detail: Dict) -> Dict:
    """Convert an EventBridge event to a notification payload."""
    type_map = {
        "HARVEST_PREDICTED": ("crop", "Harvest Prediction"),
        "PRICE_ALERT": ("subsidy", "Price Alert"),
        "PEST_DETECTED": ("crop", "Pest Alert"),
        "HEALTH_DECLINED": ("crop", "Health Alert"),
        "SCHEME_DEADLINE": ("scheme", "Scheme Deadline"),
        "APPLICATION_STATUS_CHANGED": ("application", "Application Update"),
        "INVENTORY_LOW_STOCK": ("inventory", "Low Stock Alert"),
    }
    notif_type, title_prefix = type_map.get(event_type, ("general", "Alert"))

    return {
        "type": notif_type,
        "title": f"{title_prefix}: {detail.get('title', event_type)}",
        "message": detail.get("message", f"Event: {event_type}"),
    }
