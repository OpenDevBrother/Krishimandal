"""
KrishiMandal Serverless — YouTube Search Proxy Lambda
Proxies YouTube search through multiple Invidious instances to avoid browser CORS.
"""
import json
import logging
from urllib import request as urllib_request, parse as urllib_parse

from common.fallback import fallback_to_ec2
from common.response import ok, bad_request, error

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Invidious instances to try in order (updated regularly)
INVIDIOUS_INSTANCES = [
    "https://y.com.sb",
    "https://inv.nadeko.net",
    "https://vid.puffyan.us",
    "https://invidious.nerdvpn.de",
    "https://iv.ggtyler.dev",
]

PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.r4fo.com",
    "https://api.piped.yt",
]


def _try_invidious(q: str, max_results: int) -> list | None:
    """Try Invidious instances for YouTube search."""
    for base in INVIDIOUS_INSTANCES:
        try:
            url = f"{base}/api/v1/search?q={urllib_parse.quote(q)}&type=video&region=IN"
            req = urllib_request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib_request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                if not data:
                    continue
                items = []
                for item in data:
                    vid_id = item.get("videoId", "")
                    if not vid_id:
                        continue
                    # Pick best thumbnail
                    thumbs = item.get("videoThumbnails") or []
                    thumb = ""
                    for t in thumbs:
                        if t.get("quality") == "medium":
                            thumb = t.get("url", "")
                            break
                    if not thumb and thumbs:
                        thumb = thumbs[0].get("url", "")
                    if not thumb:
                        thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"

                    items.append({
                        "videoId": vid_id,
                        "title": item.get("title", ""),
                        "channel": item.get("author", ""),
                        "thumbnail": thumb,
                        "duration": item.get("lengthSeconds", 0),
                    })
                    if len(items) >= max_results:
                        break

                if items:
                    logger.info("Invidious OK (%s): %d results", base, len(items))
                    return items
        except Exception as e:
            logger.debug("Invidious %s failed: %s", base, e)
    return None


def _try_piped(q: str, max_results: int) -> list | None:
    """Try Piped instances for YouTube search."""
    for base in PIPED_INSTANCES:
        try:
            url = f"{base}/search?q={urllib_parse.quote(q)}&filter=videos"
            req = urllib_request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib_request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                raw_items = data.get("items") or []
                items = []
                for item in raw_items:
                    if item.get("type") != "stream":
                        continue
                    vid_url = item.get("url", "")
                    vid_id = vid_url.replace("/watch?v=", "") if vid_url else ""
                    if not vid_id:
                        continue
                    thumb = item.get("thumbnail", "")
                    if not thumb:
                        thumb = f"https://img.youtube.com/vi/{vid_id}/mqdefault.jpg"
                    items.append({
                        "videoId": vid_id,
                        "title": item.get("title", ""),
                        "channel": item.get("uploaderName", ""),
                        "thumbnail": thumb,
                        "duration": item.get("duration", 0),
                    })
                    if len(items) >= max_results:
                        break

                if items:
                    logger.info("Piped OK (%s): %d results", base, len(items))
                    return items
        except Exception as e:
            logger.debug("Piped %s failed: %s", base, e)
    return None


def handler(event, context):
    """Lambda handler for GET /youtube/search."""
    try:
        qs = event.get("queryStringParameters") or {}
        q = qs.get("q", "")
        if not q:
            return bad_request("q (search query) is required.")

        max_results = int(qs.get("max_results", "12"))

        # Try Invidious first (more reliable currently)
        items = _try_invidious(q, max_results)
        if items:
            return ok({"videos": items, "source": "invidious"})

        # Fallback: Piped
        items = _try_piped(q, max_results)
        if items:
            return ok({"videos": items, "source": "piped"})

        # Fallback to EC2 backend
        fb = fallback_to_ec2(method="GET", path=f"/youtube/search?q={urllib_parse.quote(q)}&max_results={max_results}")
        if fb:
            return fb

        return ok({"videos": [], "source": "none"})

    except Exception as e:
        logger.error("YouTube search handler failed: %s", e, exc_info=True)
        fb = fallback_to_ec2(method="GET", path=f"/youtube/search?q={urllib_parse.quote(q)}&max_results=12")
        return fb or error(str(e))
