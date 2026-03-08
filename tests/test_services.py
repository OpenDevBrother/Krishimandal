"""
KrishiMandal — Tests for service layer (with fallback behavior).
"""
from __future__ import annotations


def test_llm_service_init():
    from src.services.llm_service import get_llm
    llm = get_llm()
    # Should initialize without error regardless of API key
    assert hasattr(llm, "is_available")
    assert hasattr(llm, "chat")


def test_embeddings_service_init():
    from src.services.embeddings_service import get_embeddings
    embeddings = get_embeddings()
    assert hasattr(embeddings, "is_available")
    assert hasattr(embeddings, "embed_query")


def test_vector_store_init():
    from src.services.vector_store import get_vector_store
    vs = get_vector_store()
    assert hasattr(vs, "is_available")
    assert hasattr(vs, "search")


def test_file_storage():
    from src.services.file_storage import get_file_storage
    storage = get_file_storage()
    assert hasattr(storage, "save_file")
    assert hasattr(storage, "list_files")


def test_ocr_service():
    from src.services.ocr_service import get_ocr_service
    ocr = get_ocr_service()
    result = ocr.extract_text("test_image.jpg")
    assert "document_type" in result or "extracted_text" in result


def test_twilio_service():
    from src.services.twilio_service import get_twilio_service
    twilio = get_twilio_service()
    assert hasattr(twilio, "is_available")
    # TwiML generation works even without credentials
    twiml = twilio.generate_twiml_greeting()
    assert "Response" in twiml
    assert "KrishiMandal" in twiml or "कृषिमंडल" in twiml


def test_sarvam_service():
    from src.services.sarvam_service import get_sarvam_service
    sarvam = get_sarvam_service()
    assert hasattr(sarvam, "is_available")
    assert hasattr(sarvam, "speech_to_text")
    assert hasattr(sarvam, "text_to_speech")


def test_event_bus():
    from src.events import EventBus
    bus = EventBus()
    received = []
    bus.subscribe("TEST_EVENT", lambda data: received.append(data))
    bus.publish("TEST_EVENT", {"key": "value"})
    assert len(received) == 1
    assert received[0]["key"] == "value"


def test_event_bus_log():
    from src.events import EventBus
    bus = EventBus()
    bus.publish("EVENT_1", {"a": 1})
    bus.publish("EVENT_2", {"b": 2})
    log = bus.get_event_log()
    assert len(log) == 2
