"""
KrishiMandal — Unit tests for individual agents.
"""
from __future__ import annotations

from src.agents.crop_management_agent import CropManagementAgent
from src.agents.digital_twin_agent import DigitalTwinAgent
from src.agents.learning_platform_agent import LearningPlatformAgent
from src.agents.price_predictor_agent import PricePredictorAgent
from src.agents.scheme_credit_agent import SchemeCreditAgent
from src.agents.supply_chain_agent import SupplyChainAgent


def test_digital_twin_farm_profile():
    dt = DigitalTwinAgent()
    profile = dt.get_farm_profile("F1001")
    assert profile.farmer_id == "F1001"
    assert profile.area_hectares > 0
    assert len(profile.current_crops) > 0


def test_digital_twin_handle_query_harvest():
    dt = DigitalTwinAgent()
    resp = dt.handle_query("When is my harvest?", "F1001")
    assert resp.agent_name == "digital_twin"
    assert "harvest" in resp.response_text.lower() or "crop" in resp.response_text.lower()


def test_digital_twin_handle_query_weather():
    dt = DigitalTwinAgent()
    resp = dt.handle_query("What is the weather today?", "F1001")
    assert resp.agent_name == "digital_twin"
    assert resp.confidence > 0


def test_digital_twin_simulate():
    dt = DigitalTwinAgent()
    result = dt.simulate_scenario("F1001", "drought")
    assert "recommendation" in result
    assert result["yield_impact_pct"] < 0


def test_crop_management_health():
    cm = CropManagementAgent()
    health = cm.compute_health_score("FARM-F1001")
    assert 0 <= health.health_score <= 100
    assert health.components is not None


def test_crop_management_pest():
    cm = CropManagementAgent()
    alerts = cm.predict_pest_outbreak("wheat", "FARM-F1001")
    assert isinstance(alerts, list)
    assert len(alerts) > 0


def test_crop_management_handle_query():
    cm = CropManagementAgent()
    resp = cm.handle_query("Is there any pest risk?", "F1001", crop="wheat")
    assert resp.agent_name == "crop_management"


def test_price_predictor_forecast():
    pp = PricePredictorAgent()
    forecast = pp.forecast_price("wheat")
    assert forecast.crop == "wheat"
    assert forecast.current_price > 0


def test_price_predictor_decision():
    pp = PricePredictorAgent()
    decision = pp.recommend_decision("F1001", "wheat")
    assert decision.recommendation in ["sell_now", "store_2_weeks", "wait"]


def test_price_predictor_handle_query():
    pp = PricePredictorAgent()
    resp = pp.handle_query("What is wheat price?", "F1001", crop="wheat")
    assert resp.agent_name == "price_predictor"
    assert "wheat" in resp.response_text.lower() or "₹" in resp.response_text


def test_scheme_credit_schemes():
    sc = SchemeCreditAgent()
    matches = sc.match_schemes("F1001")
    assert isinstance(matches, list)
    assert len(matches) > 0


def test_scheme_credit_score():
    sc = SchemeCreditAgent()
    score = sc.compute_credit_score("F1001")
    assert 0 <= score.score <= 100


def test_scheme_credit_handle_query():
    sc = SchemeCreditAgent()
    resp = sc.handle_query("What schemes am I eligible for?", "F1001")
    assert resp.agent_name == "scheme_credit"


def test_supply_chain_harvest_plan():
    sc = SupplyChainAgent()
    plan = sc.generate_harvest_plan("FARM-F1001", "wheat")
    assert plan.farm_id == "FARM-F1001"
    assert plan.expected_yield_quintals > 0


def test_supply_chain_markets():
    sc = SupplyChainAgent()
    options = sc.recommend_markets("wheat")
    assert isinstance(options, list)
    assert len(options) > 0


def test_supply_chain_handle_query():
    sc = SupplyChainAgent()
    resp = sc.handle_query("Where should I sell wheat?", "F1001", crop="wheat")
    assert resp.agent_name == "supply_chain"


def test_learning_platform_content():
    lp = LearningPlatformAgent()
    contents = lp.recommend_content("F1001", "pest-control")
    assert isinstance(contents, list)
    assert len(contents) > 0


def test_learning_platform_rag():
    lp = LearningPlatformAgent()
    result = lp.rag_answer("How to control pests in wheat?")
    assert "answer" in result
    assert result["answer"] != ""


def test_learning_platform_handle_query():
    lp = LearningPlatformAgent()
    resp = lp.handle_query("Tell me about organic farming", "F1001")
    assert resp.agent_name == "learning_platform"
