"""
KrishiMandal Serverless — EC2 Fallback
Forwards requests to EC2 instance when Lambda processing fails.
"""
import json
import logging
from typing import Any, Dict, Optional
from urllib import request, error as urllib_error

from common.config import config

logger = logging.getLogger(__name__)


def fallback_to_ec2(
    method: str,
    path: str,
    body: Optional[Dict] = None,
    timeout: int = 25,
) -> Optional[Dict[str, Any]]:
    """Forward a request to the EC2 fallback instance."""
    url = f"{config.EC2_FALLBACK_URL}{path}"
    logger.warning("Falling back to EC2: %s %s", method, url)

    try:
        data = json.dumps(body).encode() if body else None
        req = request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": "krishimandal-dev-key",
            },
        )
        with request.urlopen(req, timeout=timeout) as resp:
            return {
                "statusCode": resp.status,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": resp.read().decode(),
            }
    except urllib_error.HTTPError as e:
        logger.error("EC2 fallback HTTP error: %s %s", e.code, e.reason)
        return {
            "statusCode": e.code,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"detail": f"EC2 fallback error: {e.reason}"}),
        }
    except Exception as e:
        logger.error("EC2 fallback failed: %s", e)
        return None
