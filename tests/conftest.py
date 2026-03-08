"""
KrishiMandal — Pytest fixtures and test configuration.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force dummy data mode and use in-memory SQLite for tests
os.environ["USE_DUMMY_DATA"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_krishimandal.db"
os.environ["API_KEY_ENABLED"] = "false"

from src.app import app
from src.database import Base, get_db


# Test database engine
test_engine = create_engine(
    "sqlite:///./test_krishimandal.db",
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables before tests, drop after."""
    from src import db_models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    # Clean up test DB file
    try:
        os.remove("./test_krishimandal.db")
    except OSError:
        pass


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def db():
    """Test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
