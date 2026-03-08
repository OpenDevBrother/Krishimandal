"""
KrishiMandal — Tests for Applications, Inventory, and Notifications features.
"""
from __future__ import annotations

import pytest


# ══════════════════════════════════════════════════════════════════════════════
#  SETUP: Create a test farmer for all tests in this module
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True, scope="module")
def seed_test_data():
    """Create a test farmer, farm, and scheme for new feature tests."""
    from sqlalchemy import text
    from tests.conftest import TestSessionLocal

    db = TestSessionLocal()
    try:
        # Create farmer if not exists
        existing = db.execute(text("SELECT id FROM farmers WHERE id='F8001'")).fetchone()
        if not existing:
            db.execute(text(
                "INSERT INTO farmers (id, name, phone, preferred_language) "
                "VALUES ('F8001', 'Test Kisan', '+918001008001', 'hi-IN')"
            ))
            db.execute(text(
                "INSERT INTO farms (id, farmer_id, area_hectares, soil_type, irrigation_type) "
                "VALUES ('FARM-F8001', 'F8001', 2.0, 'black', 'rainfed')"
            ))
        # Create scheme if not exists
        existing_scheme = db.execute(text("SELECT id FROM schemes WHERE id='TEST_SCHEME'")).fetchone()
        if not existing_scheme:
            db.execute(text(
                "INSERT INTO schemes (id, name, benefits_inr, requirements_json, url, is_active) "
                "VALUES ('TEST_SCHEME', 'Test Yojana', 6000, '[\"Aadhaar\",\"Land Record\"]', '', 1)"
            ))
        db.commit()
    finally:
        db.close()
    yield


# ══════════════════════════════════════════════════════════════════════════════
#  APPLICATIONS
# ══════════════════════════════════════════════════════════════════════════════

class TestApplications:

    def test_create_draft_application(self, client):
        resp = client.post("/farm/F8001/applications", json={
            "scheme_id": "TEST_SCHEME",
            "farmer_notes": "Need help",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft"
        assert data["farmer_id"] == "F8001"
        assert data["scheme_id"] == "TEST_SCHEME"
        assert data["scheme_name"] == "Test Yojana"
        assert data["estimated_subsidy_inr"] == 6000.0
        assert data["farmer_notes"] == "Need help"
        assert len(data["documents_checklist"]) == 2
        assert data["documents_checklist"][0]["name"] == "Aadhaar"

    def test_create_submitted_application(self, client):
        resp = client.post("/farm/F8001/applications", json={
            "scheme_id": "TEST_SCHEME",
            "submit_directly": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None

    def test_list_applications(self, client):
        resp = client.get("/farm/F8001/applications")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        # Most recent first
        statuses = [a["status"] for a in data]
        assert "draft" in statuses
        assert "submitted" in statuses

    def test_list_applications_filter_status(self, client):
        resp = client.get("/farm/F8001/applications?status=draft")
        assert resp.status_code == 200
        data = resp.json()
        assert all(a["status"] == "draft" for a in data)

    def test_get_single_application(self, client):
        # Get the list first to find an id
        apps = client.get("/farm/F8001/applications").json()
        app_id = apps[0]["id"]
        resp = client.get(f"/farm/F8001/applications/{app_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == app_id

    def test_get_application_not_found(self, client):
        resp = client.get("/farm/F8001/applications/99999")
        assert resp.status_code == 404

    def test_get_application_wrong_farmer(self, client):
        apps = client.get("/farm/F8001/applications").json()
        app_id = apps[0]["id"]
        resp = client.get(f"/farm/WRONG/applications/{app_id}")
        assert resp.status_code == 404

    def test_submit_draft_application(self, client):
        # Find a draft
        drafts = client.get("/farm/F8001/applications?status=draft").json()
        assert len(drafts) > 0
        app_id = drafts[0]["id"]

        resp = client.put(f"/farm/F8001/applications/{app_id}", json={
            "action": "submit",
            "farmer_notes": "Updated notes",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None
        assert data["farmer_notes"] == "Updated notes"

    def test_update_application_checklist(self, client):
        # Create a fresh draft
        app = client.post("/farm/F8001/applications", json={
            "scheme_id": "TEST_SCHEME",
        }).json()
        app_id = app["id"]

        resp = client.put(f"/farm/F8001/applications/{app_id}", json={
            "action": "update",
            "documents_checklist": [
                {"name": "Aadhaar", "uploaded": True, "file_path": "/uploads/aadhaar.pdf"},
                {"name": "Land Record", "uploaded": False, "file_path": ""},
            ],
        })
        assert resp.status_code == 200
        checklist = resp.json()["documents_checklist"]
        assert checklist[0]["uploaded"] is True
        assert checklist[0]["file_path"] == "/uploads/aadhaar.pdf"

    def test_withdraw_application(self, client):
        # Create and then withdraw
        app = client.post("/farm/F8001/applications", json={
            "scheme_id": "TEST_SCHEME",
        }).json()
        app_id = app["id"]

        resp = client.delete(f"/farm/F8001/applications/{app_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "withdrawn"

    def test_withdraw_not_found(self, client):
        resp = client.delete("/farm/F8001/applications/99999")
        assert resp.status_code == 404

    def test_create_application_invalid_scheme(self, client):
        resp = client.post("/farm/F8001/applications", json={
            "scheme_id": "NONEXISTENT",
        })
        assert resp.status_code == 404

    def test_create_application_invalid_farmer(self, client):
        resp = client.post("/farm/NOBODY/applications", json={
            "scheme_id": "TEST_SCHEME",
        })
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
#  INVENTORY
# ══════════════════════════════════════════════════════════════════════════════

class TestInventory:

    def test_add_inventory_item(self, client):
        resp = client.post("/farm/F8001/inventory", json={
            "name": "Urea",
            "category": "fertilizer",
            "quantity": 50,
            "unit": "kg",
            "alert_threshold": 10,
            "purchase_price": 267,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Urea"
        assert data["category"] == "fertilizer"
        assert data["quantity"] == 50.0
        assert data["unit"] == "kg"
        assert data["alert_threshold"] == 10.0
        assert data["is_low_stock"] is False

    def test_add_inventory_item_invalid_farmer(self, client):
        resp = client.post("/farm/NOBODY/inventory", json={
            "name": "Seeds",
            "category": "seed",
        })
        assert resp.status_code == 404

    def test_list_inventory(self, client):
        resp = client.get("/farm/F8001/inventory")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["farmer_id"] == "F8001"

    def test_list_inventory_filter_category(self, client):
        # Add a seed item
        client.post("/farm/F8001/inventory", json={
            "name": "Wheat Seeds",
            "category": "seed",
            "quantity": 20,
            "unit": "kg",
        })
        resp = client.get("/farm/F8001/inventory?category=seed")
        assert resp.status_code == 200
        data = resp.json()
        assert all(i["category"] == "seed" for i in data)

    def test_get_single_inventory_item(self, client):
        items = client.get("/farm/F8001/inventory").json()
        item_id = items[0]["id"]
        resp = client.get(f"/farm/F8001/inventory/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == item_id

    def test_get_inventory_item_not_found(self, client):
        resp = client.get("/farm/F8001/inventory/99999")
        assert resp.status_code == 404

    def test_update_inventory_item(self, client):
        items = client.get("/farm/F8001/inventory").json()
        item_id = items[0]["id"]
        resp = client.put(f"/farm/F8001/inventory/{item_id}", json={
            "quantity": 100,
            "notes": "Restocked",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["quantity"] == 100.0
        assert data["notes"] == "Restocked"

    def test_update_inventory_item_not_found(self, client):
        resp = client.put("/farm/F8001/inventory/99999", json={"quantity": 5})
        assert resp.status_code == 404

    def test_adjust_stock_positive(self, client):
        items = client.get("/farm/F8001/inventory").json()
        item_id = items[0]["id"]
        old_qty = items[0]["quantity"]
        resp = client.post(f"/farm/F8001/inventory/{item_id}/adjust", json={
            "adjustment": 10,
            "reason": "New purchase",
        })
        assert resp.status_code == 200
        assert resp.json()["quantity"] == old_qty + 10

    def test_adjust_stock_negative_clamps_to_zero(self, client):
        # Create item with small quantity
        item = client.post("/farm/F8001/inventory", json={
            "name": "Neem Oil",
            "category": "pesticide",
            "quantity": 2,
            "unit": "liters",
        }).json()
        resp = client.post(f"/farm/F8001/inventory/{item['id']}/adjust", json={
            "adjustment": -100,
        })
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 0.0

    def test_adjust_stock_triggers_low_stock(self, client):
        # Create item with threshold
        item = client.post("/farm/F8001/inventory", json={
            "name": "DAP",
            "category": "fertilizer",
            "quantity": 20,
            "unit": "kg",
            "alert_threshold": 5,
        }).json()
        # Reduce below threshold
        resp = client.post(f"/farm/F8001/inventory/{item['id']}/adjust", json={
            "adjustment": -18,
        })
        assert resp.status_code == 200
        assert resp.json()["is_low_stock"] is True
        assert resp.json()["quantity"] == 2.0

    def test_low_stock_alerts(self, client):
        resp = client.get("/farm/F8001/inventory/alerts")
        assert resp.status_code == 200
        data = resp.json()
        # Should have at least the DAP item from previous test
        assert all(i["is_low_stock"] is True for i in data)

    def test_delete_inventory_item(self, client):
        item = client.post("/farm/F8001/inventory", json={
            "name": "Temp Item",
            "category": "equipment",
            "quantity": 1,
        }).json()
        resp = client.delete(f"/farm/F8001/inventory/{item['id']}")
        assert resp.status_code == 200
        # Verify deleted
        resp2 = client.get(f"/farm/F8001/inventory/{item['id']}")
        assert resp2.status_code == 404

    def test_delete_inventory_item_not_found(self, client):
        resp = client.delete("/farm/F8001/inventory/99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

class TestNotifications:

    def _seed_notification(self, client):
        """Helper: insert a notification directly for test purposes."""
        from sqlalchemy import text
        from tests.conftest import TestSessionLocal
        db = TestSessionLocal()
        try:
            db.execute(text(
                "INSERT INTO notifications (farmer_id, type, title, message, channel, is_read) "
                "VALUES ('F8001', 'general', 'Test Alert', 'This is a test notification.', 'in_app', 0)"
            ))
            db.execute(text(
                "INSERT INTO notifications (farmer_id, type, title, message, channel, is_read) "
                "VALUES ('F8001', 'price_alert', 'Price Up', 'Wheat prices rose.', 'in_app', 0)"
            ))
            db.execute(text(
                "INSERT INTO notifications (farmer_id, type, title, message, channel, is_read) "
                "VALUES ('F8001', 'general', 'Old News', 'Already read.', 'in_app', 1)"
            ))
            db.commit()
        finally:
            db.close()

    def test_auto_notification_event_fires(self, client):
        """Submitting an application should fire APPLICATION_SUBMITTED event."""
        from src.events import event_bus
        log_before = len(event_bus.get_event_log())
        client.post("/farm/F8001/applications", json={
            "scheme_id": "TEST_SCHEME",
            "submit_directly": True,
        })
        log_after = event_bus.get_event_log()
        new_events = log_after[log_before:]
        submitted_events = [e for e in new_events if e["type"] == "APPLICATION_SUBMITTED"]
        assert len(submitted_events) >= 1

    def test_low_stock_event_fires(self, client):
        """Low stock adjustment should fire INVENTORY_LOW_STOCK event."""
        from src.events import event_bus
        item = client.post("/farm/F8001/inventory", json={
            "name": "Event Test Item",
            "category": "pesticide",
            "quantity": 10,
            "unit": "liters",
            "alert_threshold": 5,
        }).json()
        log_before = len(event_bus.get_event_log())
        client.post(f"/farm/F8001/inventory/{item['id']}/adjust", json={
            "adjustment": -8,
        })
        log_after = event_bus.get_event_log()
        new_events = log_after[log_before:]
        low_stock_events = [e for e in new_events if e["type"] == "INVENTORY_LOW_STOCK"]
        assert len(low_stock_events) >= 1
        assert low_stock_events[0]["data"]["item_name"] == "Event Test Item"

    def test_list_notifications(self, client):
        self._seed_notification(client)
        resp = client.get("/farm/F8001/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert "type" in data[0]
        assert "title" in data[0]
        assert "message" in data[0]

    def test_list_notifications_filter_type(self, client):
        resp = client.get("/farm/F8001/notifications?type=price_alert")
        assert resp.status_code == 200
        data = resp.json()
        assert all(n["type"] == "price_alert" for n in data)

    def test_list_notifications_filter_read(self, client):
        resp = client.get("/farm/F8001/notifications?is_read=false")
        assert resp.status_code == 200
        data = resp.json()
        assert all(n["is_read"] is False for n in data)

    def test_unread_count(self, client):
        resp = client.get("/farm/F8001/notifications/unread-count")
        assert resp.status_code == 200
        data = resp.json()
        assert data["farmer_id"] == "F8001"
        assert isinstance(data["unread_count"], int)
        assert data["unread_count"] >= 0

    def test_mark_single_notification_read(self, client):
        # Get an unread notification
        notifs = client.get("/farm/F8001/notifications?is_read=false").json()
        if not notifs:
            pytest.skip("No unread notifications")
        notif_id = notifs[0]["id"]

        resp = client.put(f"/farm/F8001/notifications/{notif_id}/read")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_read"] is True
        assert data["read_at"] is not None

    def test_mark_notification_read_not_found(self, client):
        resp = client.put("/farm/F8001/notifications/99999/read")
        assert resp.status_code == 404

    def test_mark_all_read(self, client):
        resp = client.put("/farm/F8001/notifications/read-all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["farmer_id"] == "F8001"
        assert isinstance(data["marked_read"], int)
        # Verify all are read now
        unread = client.get("/farm/F8001/notifications/unread-count").json()
        assert unread["unread_count"] == 0

    def test_delete_notification(self, client):
        notifs = client.get("/farm/F8001/notifications").json()
        if not notifs:
            pytest.skip("No notifications to delete")
        notif_id = notifs[0]["id"]

        resp = client.delete(f"/farm/F8001/notifications/{notif_id}")
        assert resp.status_code == 200
        # Verify deleted
        resp2 = client.put(f"/farm/F8001/notifications/{notif_id}/read")
        assert resp2.status_code == 404

    def test_delete_notification_not_found(self, client):
        resp = client.delete("/farm/F8001/notifications/99999")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATOR ROUTING
# ══════════════════════════════════════════════════════════════════════════════

class TestOrchestratorRouting:

    def test_application_keywords_route_to_scheme_credit(self, client):
        from src.orchestrator import SupervisorOrchestrator
        orch = SupervisorOrchestrator()
        targets = orch._classify_query("show my applications")
        assert "scheme_credit" in targets

    def test_inventory_keywords_route_to_digital_twin(self, client):
        from src.orchestrator import SupervisorOrchestrator
        orch = SupervisorOrchestrator()
        targets = orch._classify_query("check my inventory stock")
        assert "digital_twin" in targets

    def test_notification_keywords_route_to_digital_twin(self, client):
        from src.orchestrator import SupervisorOrchestrator
        orch = SupervisorOrchestrator()
        targets = orch._classify_query("show unread notifications")
        assert "digital_twin" in targets
