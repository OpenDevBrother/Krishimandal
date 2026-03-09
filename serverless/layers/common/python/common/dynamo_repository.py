"""
KrishiMandal Serverless — DynamoDB Repository
Single-table design replacing SQLAlchemy/SQLite.

Key Schema:
  PK: FARM#{farmer_id}   SK: PROFILE
  PK: FARM#{farmer_id}   SK: STATE#{timestamp}
  PK: FARM#{farmer_id}   SK: APP#{app_id}
  PK: FARM#{farmer_id}   SK: INV#{item_id}
  PK: FARM#{farmer_id}   SK: NOTIF#{notif_id}
  PK: FARM#{farmer_id}   SK: CROP#{crop_id}
  PK: PRICE#{crop}       SK: {mandi}#{timestamp}
  PK: SCHEME#{scheme_id}  SK: META

GSI1:
  GSI1PK: TYPE#APPLICATION  GSI1SK: {status}#{timestamp}
  GSI1PK: TYPE#NOTIFICATION GSI1SK: {farmer_id}#{read}#{timestamp}
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr

from common.config import config

logger = logging.getLogger(__name__)


class DynamoRepository:
    def __init__(self):
        self._dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
        self._table = self._dynamodb.Table(config.TABLE_NAME)

    # ── Farm Profile ─────────────────────────────────────────────
    def get_farm(self, farmer_id: str) -> Optional[Dict]:
        resp = self._table.get_item(Key={"PK": f"FARM#{farmer_id}", "SK": "PROFILE"})
        return resp.get("Item")

    def save_farm(self, farmer_id: str, data: Dict) -> Dict:
        item = {
            "PK": f"FARM#{farmer_id}",
            "SK": "PROFILE",
            "farmer_id": farmer_id,
            "entity_type": "FARM_PROFILE",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        self._table.put_item(Item=item)
        return item

    def update_farm(self, farmer_id: str, updates: Dict) -> Optional[Dict]:
        expr_parts, values, names = [], {}, {}
        for i, (k, v) in enumerate(updates.items()):
            key = f"#k{i}"
            val = f":v{i}"
            expr_parts.append(f"{key} = {val}")
            names[key] = k
            values[val] = v
        if not expr_parts:
            return self.get_farm(farmer_id)
        expr_parts.append("#upd = :upd_val")
        names["#upd"] = "updated_at"
        values[":upd_val"] = datetime.now(timezone.utc).isoformat()

        resp = self._table.update_item(
            Key={"PK": f"FARM#{farmer_id}", "SK": "PROFILE"},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")

    # ── Applications ─────────────────────────────────────────────
    def create_application(self, farmer_id: str, data: Dict) -> Dict:
        app_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"FARM#{farmer_id}",
            "SK": f"APP#{app_id}",
            "GSI1PK": "TYPE#APPLICATION",
            "GSI1SK": f"{data.get('status', 'draft')}#{now}",
            "id": app_id,
            "farmer_id": farmer_id,
            "entity_type": "APPLICATION",
            "created_at": now,
            "updated_at": now,
            **data,
        }
        self._table.put_item(Item=item)
        return item

    def get_applications(self, farmer_id: str) -> List[Dict]:
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(f"FARM#{farmer_id}") & Key("SK").begins_with("APP#"),
        )
        return resp.get("Items", [])

    # ── Inventory ────────────────────────────────────────────────
    def create_inventory_item(self, farmer_id: str, data: Dict) -> Dict:
        item_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"FARM#{farmer_id}",
            "SK": f"INV#{item_id}",
            "id": item_id,
            "farmer_id": farmer_id,
            "entity_type": "INVENTORY",
            "created_at": now,
            "updated_at": now,
            **data,
        }
        self._table.put_item(Item=item)
        return item

    def get_inventory(self, farmer_id: str) -> List[Dict]:
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(f"FARM#{farmer_id}") & Key("SK").begins_with("INV#"),
        )
        return resp.get("Items", [])

    def get_inventory_item(self, farmer_id: str, item_id: str) -> Optional[Dict]:
        resp = self._table.get_item(Key={"PK": f"FARM#{farmer_id}", "SK": f"INV#{item_id}"})
        return resp.get("Item")

    def update_inventory_item(self, farmer_id: str, item_id: str, updates: Dict) -> Optional[Dict]:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        expr_parts, values, names = [], {}, {}
        for i, (k, v) in enumerate(updates.items()):
            expr_parts.append(f"#k{i} = :v{i}")
            names[f"#k{i}"] = k
            values[f":v{i}"] = v
        resp = self._table.update_item(
            Key={"PK": f"FARM#{farmer_id}", "SK": f"INV#{item_id}"},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return resp.get("Attributes")

    def delete_inventory_item(self, farmer_id: str, item_id: str):
        self._table.delete_item(Key={"PK": f"FARM#{farmer_id}", "SK": f"INV#{item_id}"})

    def get_low_stock_items(self, farmer_id: str) -> List[Dict]:
        items = self.get_inventory(farmer_id)
        return [i for i in items if i.get("quantity", 0) <= i.get("alert_threshold", 0)]

    # ── Notifications ────────────────────────────────────────────
    def create_notification(self, farmer_id: str, data: Dict) -> Dict:
        notif_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"FARM#{farmer_id}",
            "SK": f"NOTIF#{notif_id}",
            "id": notif_id,
            "farmer_id": farmer_id,
            "entity_type": "NOTIFICATION",
            "is_read": False,
            "created_at": now,
            **data,
        }
        self._table.put_item(Item=item)
        return item

    def get_notifications(self, farmer_id: str) -> List[Dict]:
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(f"FARM#{farmer_id}") & Key("SK").begins_with("NOTIF#"),
            ScanIndexForward=False,
        )
        return resp.get("Items", [])

    def get_unread_count(self, farmer_id: str) -> int:
        items = self.get_notifications(farmer_id)
        return sum(1 for i in items if not i.get("is_read", False))

    def mark_notification_read(self, farmer_id: str, notif_id: str):
        self._table.update_item(
            Key={"PK": f"FARM#{farmer_id}", "SK": f"NOTIF#{notif_id}"},
            UpdateExpression="SET is_read = :val",
            ExpressionAttributeValues={":val": True},
        )

    def mark_all_notifications_read(self, farmer_id: str):
        notifs = self.get_notifications(farmer_id)
        for n in notifs:
            if not n.get("is_read"):
                self.mark_notification_read(farmer_id, n["id"])

    # ── Schemes ──────────────────────────────────────────────────
    def get_schemes(self) -> List[Dict]:
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq("SCHEMES") & Key("SK").begins_with("SCH#"),
        )
        return resp.get("Items", [])

    def save_scheme(self, scheme_id: str, data: Dict):
        self._table.put_item(Item={
            "PK": "SCHEMES",
            "SK": f"SCH#{scheme_id}",
            "id": scheme_id,
            "entity_type": "SCHEME",
            **data,
        })

    # ── Prices ───────────────────────────────────────────────────
    def save_price(self, crop: str, mandi: str, price: float):
        now = datetime.now(timezone.utc).isoformat()
        self._table.put_item(Item={
            "PK": f"PRICE#{crop}",
            "SK": f"{mandi}#{now}",
            "crop": crop, "mandi": mandi, "price": str(price),
            "entity_type": "PRICE",
            "recorded_at": now,
        })

    def get_latest_price(self, crop: str, mandi: str = "Indore") -> Optional[Dict]:
        resp = self._table.query(
            KeyConditionExpression=Key("PK").eq(f"PRICE#{crop}") & Key("SK").begins_with(f"{mandi}#"),
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None


# Singleton
_repo: Optional[DynamoRepository] = None

def get_repository() -> DynamoRepository:
    global _repo
    if _repo is None:
        _repo = DynamoRepository()
    return _repo
