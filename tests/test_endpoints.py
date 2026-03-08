"""
KrishiMandal — Integration tests for API endpoints.
"""
from __future__ import annotations


def test_root(client):
    """Root endpoint returns platform info."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["platform"] == "KrishiMandal"
    assert data["status"] == "running"
    assert data["agents"] == 6


def test_health_check(client):
    """Health endpoint returns status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "database" in data


def test_list_agents(client):
    """Agents endpoint returns 6 agents."""
    resp = client.get("/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) == 6
    names = [a["name"] for a in agents]
    assert "digital_twin" in names
    assert "price_predictor" in names


def test_get_farm_profile(client):
    """Farm profile endpoint returns valid data."""
    resp = client.get("/farm/F1001")
    assert resp.status_code == 200
    data = resp.json()
    assert "farmer_id" in data
    assert "area_hectares" in data
    assert "current_crops" in data


def test_get_farm_state(client):
    """Farm state endpoint returns NDVI and moisture."""
    resp = client.get("/farm/F1001/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "ndvi_mean" in data
    assert "soil_moisture_pct" in data


def test_get_crop_health(client):
    """Crop health endpoint returns score and components."""
    resp = client.get("/farm/F1001/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "health_score" in data
    assert "components" in data


def test_get_scheme_matches(client):
    """Scheme matches endpoint returns list."""
    resp = client.get("/farm/F1001/schemes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "scheme_name" in data[0]


def test_price_forecast(client):
    """Price forecast endpoint returns forecast data."""
    resp = client.get("/price/wheat")
    assert resp.status_code == 200
    data = resp.json()
    assert data["crop"] == "wheat"
    assert "current_price" in data
    assert "forecast_7day" in data


def test_harvest_plan(client):
    """Harvest plan endpoint returns plan."""
    resp = client.get("/farm/F1001/harvest-plan")
    assert resp.status_code == 200
    data = resp.json()
    assert "harvest_date" in data
    assert "expected_yield_quintals" in data


def test_query_endpoint(client):
    """Query endpoint routes and returns response."""
    resp = client.post("/query", json={
        "query": "What is the price of wheat?",
        "farmer_id": "F1001",
        "language": "hi-IN",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "final_response" in data
    assert "agents_invoked" in data
    assert len(data["agents_invoked"]) > 0


def test_simulate_scenario(client):
    """Scenario simulation returns result."""
    resp = client.post("/farm/F1001/simulate", json={"scenario": "drought"})
    assert resp.status_code == 200
    data = resp.json()
    assert "scenario" in data
    assert "recommendation" in data


def test_learning_content(client):
    """Learning content endpoint returns content list."""
    resp = client.get("/learning/content?topic=pest-control")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_price_history(client):
    """Price history returns records structure."""
    resp = client.get("/price/wheat/history?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["crop"] == "wheat"
    assert "records" in data


def test_ocr_document(client):
    """OCR endpoint returns extraction result."""
    resp = client.post("/documents/ocr?image_path=test.jpg")
    assert resp.status_code == 200
    data = resp.json()
    assert "document_type" in data or "extracted_text" in data


def test_create_farm(client):
    """Create farm endpoint creates a new farmer."""
    resp = client.post("/farm", json={
        "farmer_id": "F9999",
        "farmer_name": "Test Farmer",
        "phone": "+919999999999",
        "area_hectares": 2.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["farmer_id"] == "F9999"
    assert data["farm_id"] == "FARM-F9999"


def test_create_farm_duplicate(client):
    """Creating duplicate farmer returns 409."""
    # First ensure F9999 exists from previous test
    resp = client.post("/farm", json={
        "farmer_id": "F9999",
        "farmer_name": "Test Farmer",
        "phone": "+919999999998",
        "area_hectares": 2.0,
    })
    assert resp.status_code == 409


def test_update_farm(client):
    """Update farm endpoint modifies farmer data."""
    resp = client.put("/farm/F9999", json={
        "farmer_name": "Updated Farmer",
        "area_hectares": 3.5,
    })
    assert resp.status_code == 200


def test_add_crop(client):
    """Add crop to farm."""
    resp = client.post("/farm/F9999/crops", json={
        "crop_type": "wheat",
        "area_hectares": 1.5,
        "variety": "HD-2967",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["farm_id"] == "FARM-F9999"


def test_delete_farm(client):
    """Delete farmer and all data."""
    resp = client.delete("/farm/F9999")
    assert resp.status_code == 200


def test_delete_farm_not_found(client):
    """Delete non-existent farmer returns 404."""
    resp = client.delete("/farm/NONEXISTENT")
    assert resp.status_code == 404
