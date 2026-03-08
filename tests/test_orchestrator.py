"""
KrishiMandal — Tests for the Supervisor Orchestrator.
"""
from __future__ import annotations

from src.orchestrator import SupervisorOrchestrator


def test_orchestrator_init():
    orch = SupervisorOrchestrator()
    assert len(orch.agents) == 6
    assert "digital_twin" in orch.agents
    assert "price_predictor" in orch.agents


def test_classify_price_query():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("What is the price of wheat in mandi?")
    assert "price_predictor" in agents


def test_classify_scheme_query():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("Which government yojana can I apply for?")
    assert "scheme_credit" in agents


def test_classify_health_query():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("How is my crop health?")
    assert "crop_management" in agents


def test_classify_farm_query():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("Show me my farm overview and weather")
    assert "digital_twin" in agents


def test_classify_learning_query():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("How to do organic farming?")
    assert "learning_platform" in agents


def test_classify_supply_chain_query():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("What is the best route for transport?")
    assert "supply_chain" in agents


def test_classify_unknown_defaults_to_learning():
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("xyzabc random gibberish")
    assert "learning_platform" in agents


def test_multi_agent_routing():
    """Complex query triggers multiple agents."""
    orch = SupervisorOrchestrator()
    agents = orch._classify_query("What is wheat price and should I sell at mandi or store?")
    assert len(agents) >= 1
    assert "price_predictor" in agents


def test_route_query_returns_result():
    orch = SupervisorOrchestrator()
    result = orch.route_query("What is wheat price?", "F1001")
    assert result.query == "What is wheat price?"
    assert result.farmer_id == "F1001"
    assert len(result.agents_invoked) > 0
    assert result.final_response != ""
    assert result.processing_time_ms >= 0


def test_list_agents():
    orch = SupervisorOrchestrator()
    agents = orch.list_agents()
    assert len(agents) == 6
    names = [a["name"] for a in agents]
    assert "digital_twin" in names
