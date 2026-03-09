"""
KrishiMandal Serverless — API Gateway Lambda Response Helpers
"""
import json
from typing import Any
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def api_response(status_code: int, body: Any = None, headers: dict = None) -> dict:
    """Build a standard API Gateway proxy response."""
    resp = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-API-Key,Authorization",
            **(headers or {}),
        },
    }
    if body is not None:
        resp["body"] = json.dumps(body, cls=DecimalEncoder)
    else:
        resp["body"] = ""
    return resp


def ok(body: Any = None) -> dict:
    return api_response(200, body)


def created(body: Any = None) -> dict:
    return api_response(201, body)


def no_content() -> dict:
    return api_response(204)


def bad_request(message: str = "Bad request") -> dict:
    return api_response(400, {"detail": message})


def not_found(message: str = "Not found") -> dict:
    return api_response(404, {"detail": message})


def error(message: str = "Internal server error") -> dict:
    return api_response(500, {"detail": message})
