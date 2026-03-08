"""
KrishiMandal — Simple in-process event bus for cross-agent communication.
In production, this maps to Amazon EventBridge.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


# Event type constants
HARVEST_PREDICTED = "HARVEST_PREDICTED"
PRICE_ALERT = "PRICE_ALERT"
PEST_DETECTED = "PEST_DETECTED"
HEALTH_DECLINED = "HEALTH_DECLINED"
FARM_CREATED = "FARM_CREATED"
SCHEME_DEADLINE = "SCHEME_DEADLINE"
APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED"
INVENTORY_LOW_STOCK = "INVENTORY_LOW_STOCK"


class EventBus:
    """
    Simple pub/sub event bus. Handlers are called synchronously.
    For async execution, callers should use FastAPI BackgroundTasks.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_log: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, handler: Callable):
        """Register a handler for an event type."""
        self._subscribers[event_type].append(handler)
        logger.info("Subscribed %s to event: %s", handler.__name__, event_type)

    def publish(self, event_type: str, data: Dict[str, Any] = None):
        """Publish an event. All subscribers are called synchronously."""
        data = data or {}
        event = {"type": event_type, "data": data}
        self._event_log.append(event)
        logger.info("Event published: %s (data keys: %s)", event_type, list(data.keys()))

        for handler in self._subscribers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                logger.error("Event handler %s failed: %s", handler.__name__, e, exc_info=True)

    def get_event_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent events for debugging."""
        return self._event_log[-limit:]


# Global event bus singleton
event_bus = EventBus()


def setup_notification_handlers():
    """Subscribe to events and auto-create notifications."""

    def _on_application_submitted(data: Dict[str, Any]):
        from src.database import SessionLocal
        from src.repositories import create_notification
        db = SessionLocal()
        try:
            create_notification(
                db,
                farmer_id=data.get("farmer_id", ""),
                type="application_update",
                title="Application Submitted",
                message=f"Your application for scheme {data.get('scheme_id', '')} has been submitted successfully.",
                related_entity_type="application",
                related_entity_id=str(data.get("application_id", "")),
            )
        finally:
            db.close()

    def _on_application_status_changed(data: Dict[str, Any]):
        from src.database import SessionLocal
        from src.repositories import create_notification
        db = SessionLocal()
        try:
            create_notification(
                db,
                farmer_id=data.get("farmer_id", ""),
                type="application_update",
                title="Application Status Updated",
                message=f"Your application status has been updated to: {data.get('status', '')}.",
                related_entity_type="application",
                related_entity_id=str(data.get("application_id", "")),
            )
        finally:
            db.close()

    def _on_price_alert(data: Dict[str, Any]):
        from src.database import SessionLocal
        from src.repositories import create_notification
        db = SessionLocal()
        try:
            create_notification(
                db,
                farmer_id=data.get("farmer_id", ""),
                type="price_alert",
                title="Price Alert",
                message=data.get("message", "Price change detected for your crop."),
            )
        finally:
            db.close()

    def _on_pest_detected(data: Dict[str, Any]):
        from src.database import SessionLocal
        from src.repositories import create_notification
        db = SessionLocal()
        try:
            create_notification(
                db,
                farmer_id=data.get("farmer_id", ""),
                type="pest_warning",
                title="Pest Warning",
                message=data.get("response", "Pest activity detected in your area."),
            )
        finally:
            db.close()

    def _on_inventory_low_stock(data: Dict[str, Any]):
        from src.database import SessionLocal
        from src.repositories import create_notification
        db = SessionLocal()
        try:
            item_name = data.get("item_name", "item")
            create_notification(
                db,
                farmer_id=data.get("farmer_id", ""),
                type="inventory_alert",
                title=f"Low Stock: {item_name}",
                message=f"Your stock of {item_name} is running low ({data.get('quantity', 0)} {data.get('unit', 'units')} remaining).",
                related_entity_type="inventory_item",
                related_entity_id=str(data.get("item_id", "")),
            )
        finally:
            db.close()

    def _on_scheme_deadline(data: Dict[str, Any]):
        from src.database import SessionLocal
        from src.repositories import create_notification
        db = SessionLocal()
        try:
            create_notification(
                db,
                farmer_id=data.get("farmer_id", ""),
                type="scheme_deadline",
                title="Scheme Deadline Approaching",
                message=data.get("message", "A scheme deadline is approaching."),
                related_entity_type="scheme",
                related_entity_id=str(data.get("scheme_id", "")),
            )
        finally:
            db.close()

    event_bus.subscribe(APPLICATION_SUBMITTED, _on_application_submitted)
    event_bus.subscribe(APPLICATION_STATUS_CHANGED, _on_application_status_changed)
    event_bus.subscribe(PRICE_ALERT, _on_price_alert)
    event_bus.subscribe(PEST_DETECTED, _on_pest_detected)
    event_bus.subscribe(INVENTORY_LOW_STOCK, _on_inventory_low_stock)
    event_bus.subscribe(SCHEME_DEADLINE, _on_scheme_deadline)
    logger.info("Notification event handlers registered.")
