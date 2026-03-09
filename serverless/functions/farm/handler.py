"""
KrishiMandal Serverless — Farm Lambda
Farm profile CRUD, state, health, crop management, simulation.
"""
import json
import logging
import random
from datetime import date, timedelta
from typing import Optional

from common.bedrock_service import get_bedrock_llm
from common.dynamo_repository import get_repository
from common.fallback import fallback_to_ec2
from common.response import ok, created, bad_request, not_found, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _extract_farmer_id(path: str) -> Optional[str]:
    """Extract farmer_id from /farm/{farmer_id}... paths."""
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "farm":
        return parts[1]
    return None


def _dummy_farm_state(farmer_id: str) -> dict:
    """Generate dummy farm state data."""
    return {
        "farm_id": f"FARM-{farmer_id}",
        "ndvi_mean": round(random.uniform(0.45, 0.82), 2),
        "soil_moisture_pct": round(random.uniform(25, 65), 1),
        "weather": {
            "temperature_c": round(random.uniform(18, 38), 1),
            "humidity_pct": round(random.uniform(30, 80), 1),
            "rainfall_mm": round(random.uniform(0, 15), 1),
            "wind_speed_kmh": round(random.uniform(5, 25), 1),
            "condition": random.choice(["clear", "partly_cloudy", "cloudy", "light_rain"]),
        },
        "health_score": round(random.uniform(60, 95), 1),
    }


def _dummy_crop_health(farmer_id: str) -> dict:
    """Generate dummy crop health data."""
    soil = random.randint(14, 24)
    season = random.randint(14, 24)
    stage = random.randint(14, 24)
    weather = random.randint(14, 24)
    return {
        "farm_id": f"FARM-{farmer_id}",
        "health_score": soil + season + stage + weather,
        "ndvi_mean": round(random.uniform(0.45, 0.82), 2),
        "components": {
            "soil_score": soil,
            "season_score": season,
            "stage_score": stage,
            "weather_score": weather,
        },
    }


def handler(event, context):
    """Lambda handler for /farm/* endpoints."""
    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        farmer_id = path_params.get("farmer_id") or _extract_farmer_id(path)
        repo = get_repository()

        # POST /farm — create new farm profile
        if method == "POST" and (path == "/farm" or path.rstrip("/") == "/farm"):
            body = json.loads(event.get("body", "{}"))
            fid = body.get("farmer_id")
            if not fid:
                return bad_request("farmer_id is required.")

            existing = repo.get_farm(fid)
            if existing:
                return bad_request(f"Farmer {fid} already exists.")

            data = {
                "farmer_name": body.get("farmer_name", ""),
                "phone": body.get("phone", ""),
                "preferred_language": body.get("preferred_language", "hi-IN"),
                "area_hectares": body.get("area_hectares", 0),
                "soil_type": body.get("soil_type", ""),
                "irrigation_type": body.get("irrigation_type", ""),
                "location_lat": body.get("location_lat", 0),
                "location_lng": body.get("location_lng", 0),
            }
            item = repo.save_farm(fid, data)
            return created({"message": "Farm profile created.", "farmer_id": fid})

        if not farmer_id:
            return bad_request("farmer_id is required in path.")

        # GET /farm/{farmer_id}/state
        if method == "GET" and path.endswith("/state"):
            state = _dummy_farm_state(farmer_id)
            return ok(state)

        # GET /farm/{farmer_id}/health
        if method == "GET" and path.endswith("/health"):
            health = _dummy_crop_health(farmer_id)
            return ok(health)

        # GET /farm/{farmer_id}/schemes — delegate to schemes lambda
        if method == "GET" and path.endswith("/schemes"):
            return ok(_dummy_scheme_matches())

        # POST /farm/{farmer_id}/simulate
        if method == "POST" and path.endswith("/simulate"):
            body = json.loads(event.get("body", "{}"))
            scenario = body.get("scenario", "drought")
            llm = get_bedrock_llm()
            farm = repo.get_farm(farmer_id) or {}
            crop = farm.get("current_crop", "wheat")

            result = llm.chat(
                messages=[{"role": "user", "content": f"Simulate a '{scenario}' scenario for a farm growing {crop} in Maharashtra, India. Provide impact analysis and recommendations."}],
                system_prompt="You are a digital twin simulator for Indian farms. Provide realistic scenario analysis with specific numbers.",
                max_tokens=512,
            )
            return ok({
                "farmer_id": farmer_id,
                "scenario": scenario,
                "analysis": result,
            })

        # POST /farm/{farmer_id}/crops
        if method == "POST" and path.endswith("/crops"):
            body = json.loads(event.get("body", "{}"))
            farm = repo.get_farm(farmer_id)
            if not farm:
                return not_found(f"Farm for farmer {farmer_id} not found.")
            # Store crop info in farm profile
            updates = {"current_crop": body.get("crop_type", "")}
            repo.update_farm(farmer_id, updates)
            return created({"message": "Crop added.", "farmer_id": farmer_id})

        # GET /farm/{farmer_id} — get profile
        if method == "GET":
            farm = repo.get_farm(farmer_id)
            if not farm:
                # Return dummy profile
                return ok({
                    "farm_id": f"FARM-{farmer_id}",
                    "farmer_id": farmer_id,
                    "farmer_name": "Rajesh Patil",
                    "area_hectares": 2.5,
                    "soil_type": "black_cotton",
                    "irrigation_type": "drip",
                    "current_crops": [{"crop_type": "wheat", "growth_stage": "vegetative", "health_score": 78}],
                })
            return ok(farm)

        # PUT /farm/{farmer_id} — update profile
        if method == "PUT":
            body = json.loads(event.get("body", "{}"))
            updates = {k: v for k, v in body.items() if v is not None and k != "farmer_id"}
            result = repo.update_farm(farmer_id, updates)
            if not result:
                return not_found(f"Farmer {farmer_id} not found.")
            return ok({"message": "Farm profile updated.", "farmer_id": farmer_id})

        # DELETE /farm/{farmer_id}
        if method == "DELETE":
            # DynamoDB delete — just remove the profile item
            repo._table.delete_item(Key={"PK": f"FARM#{farmer_id}", "SK": "PROFILE"})
            return ok({"message": "Farmer deleted.", "farmer_id": farmer_id})

        return bad_request("Unsupported operation.")

    except Exception as e:
        logger.error("Farm handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(method=event.get("httpMethod", "GET"), path=event.get("path", "/farm"))
        return fb or error(str(e))


def _dummy_scheme_matches():
    """Dummy scheme matches for /farm/{id}/schemes."""
    schemes = [
        {"scheme_id": "PMKISAN", "scheme_name": "PM-KISAN Samman Nidhi", "eligibility_score": 0.95, "benefits_inr": 6000},
        {"scheme_id": "PMFBY", "scheme_name": "PM Fasal Bima Yojana", "eligibility_score": 0.88, "benefits_inr": 25000},
        {"scheme_id": "KCC", "scheme_name": "Kisan Credit Card", "eligibility_score": 0.82, "benefits_inr": 300000},
        {"scheme_id": "PMKUSUM", "scheme_name": "PM-KUSUM Solar Pump", "eligibility_score": 0.75, "benefits_inr": 50000},
    ]
    return schemes
