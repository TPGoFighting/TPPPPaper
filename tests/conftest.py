"""Shared pytest fixtures for TPaper test suite.

Provides:
- test_settings: patched Settings with safe test defaults
- db_engine / db_session: in-memory SQLite with all tables created
- test_client: FastAPI TestClient with auth override + DB override
- admin_cookie: valid session cookie for authenticated requests
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend/ is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set test env vars BEFORE importing app modules
os.environ.setdefault("MASTER_SECRET", "test-secret-must-be-at-least-32-chars-long!!")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-32-chars-long!!")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")


@pytest.fixture(scope="session")
def test_settings():
    """Provide a Settings instance with safe test defaults."""
    from app.config import Settings

    return Settings(
        master_secret="test-secret-must-be-at-least-32-chars-long!!",
        session_secret="test-session-secret-32-chars-long!!",
        database_url="sqlite:///:memory:",
        admin_username="testadmin",
        admin_password_hash="",
        storage_root="/tmp/tpaper-test-storage",
        redis_url="",
    )


@pytest.fixture(scope="function")
def db_engine(test_settings):
    """Create an in-memory SQLite engine with all tables."""
    from app.database import Base
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide a transactional database session for tests."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_client(db_engine, test_settings):
    """Provide a FastAPI TestClient with auth bypass and test DB."""
    from fastapi.testclient import TestClient

    from app.database import Base, get_db
    from app.deps import require_auth
    from app.main import app

    # Override DB
    TestSession = sessionmaker(bind=db_engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    # Override auth to return test admin
    def override_require_auth():
        return "test_admin"

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_auth] = override_require_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauth_client(db_engine):
    """Provide a FastAPI TestClient WITHOUT auth bypass (for auth testing)."""
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    TestSession = sessionmaker(bind=db_engine)

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_cookie(test_settings):
    """Generate a valid admin session cookie value."""
    from itsdangerous import URLSafeTimedSerializer

    serializer = URLSafeTimedSerializer(test_settings.session_secret, salt="tpaper-session")
    return serializer.dumps({"username": "testadmin"})
