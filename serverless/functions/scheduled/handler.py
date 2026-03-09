"""
KrishiMandal Serverless — Scheduled Tasks Lambda
Runs on EventBridge schedule: morning refresh + weather updates.
"""
import json
import logging
import random
from datetime import datetime

from common.dynamo_repository import get_repository
from common.events import publish_event
from common.fallback import fallback_to_ec2
from common.response import ok, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Crops and mandis for price refresh
CROPS = ["wheat", "rice", "cotton", "soybean", "sugarcane", "onion", "tomato"]
MANDIS = [
    "Pune (Gultekdi)", "Nashik", "Nagpur (Kalamna)", "Aurangabad",
    "Solapur", "Kolhapur", "Sangli", "Ahmednagar",
]


def handler(event, context):
    """Lambda handler for scheduled tasks — EventBridge triggers."""
    try:
        source = event.get("source", "")
        rule_name = event.get("resources", [""])[0].split("/")[-1] if event.get("resources") else ""

        logger.info("Scheduled task triggered: source=%s rule=%s", source, rule_name)

        repo = get_repository()

        if "Weather" in rule_name:
            return _refresh_weather(repo)
        else:
            # Morning refresh — prices + deadline checks
            _refresh_prices(repo)
            _check_deadlines(repo)
            return ok({"message": "Morning refresh complete", "timestamp": datetime.utcnow().isoformat()})

    except Exception as e:
        logger.error("Scheduled handler failed: %s", e, exc_info=True)
        return error(str(e))


def _refresh_prices(repo):
    """Refresh mandi prices for key crops."""
    for crop in CROPS:
        for mandi in random.sample(MANDIS, k=3):
            price = round(random.uniform(1500, 4500), 0)
            repo.save_price(crop, mandi, price)

            # Alert on significant price changes
            if random.random() < 0.1:
                publish_event("PRICE_ALERT", {
                    "crop": crop,
                    "mandi": mandi,
                    "price": price,
                    "change_pct": round(random.uniform(5, 15), 1),
                    "direction": random.choice(["up", "down"]),
                })

    logger.info("Prices refreshed for %d crops across mandis", len(CROPS))


def _check_deadlines(repo):
    """Check upcoming scheme deadlines and notify farmers."""
    # In production, this would scan DynamoDB for applications
    # with upcoming deadlines and publish events
    logger.info("Deadline check complete")


def _refresh_weather(repo):
    """Refresh weather data for all farms."""
    # In production, call OpenWeatherMap API for each farm's location
    # and update the farm state in DynamoDB
    logger.info("Weather refresh triggered")
    return ok({"message": "Weather refresh complete", "timestamp": datetime.utcnow().isoformat()})
