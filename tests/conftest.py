import asyncio
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

from src.database import get_async_session
from src.auth.db import Base as AuthBase
from src.models import Base as ModelBase
from src.main import app as main_app

TEST_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
TEST_SQLALCHEMY_DATABASE_URL_SYNC = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def sync_engine():
    engine = create_engine(
        TEST_SQLALCHEMY_DATABASE_URL_SYNC,
        connect_args={"check_same_thread": False}
    )
    yield engine


@pytest.fixture(scope="function")
def setup_database(sync_engine):
    ModelBase.metadata.create_all(bind=sync_engine)
    AuthBase.metadata.create_all(bind=sync_engine)

    yield

    ModelBase.metadata.drop_all(bind=sync_engine)
    AuthBase.metadata.drop_all(bind=sync_engine)


@pytest.fixture(scope="function")
def sync_session_factory(sync_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


@pytest.fixture(scope="function")
def sync_session(sync_session_factory, setup_database):
    db = sync_session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def mock_test_user():
    """Create a mock test user for tests."""
    user_id = uuid.uuid4()
    user = MagicMock()
    user.id = user_id
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    user.is_verified = True
    return user


@pytest.fixture(scope="function")
def mock_test_admin():
    """Create a mock admin user for tests."""
    admin_id = uuid.uuid4()
    admin = MagicMock()
    admin.id = admin_id
    admin.email = "admin@example.com"
    admin.is_active = True
    admin.is_superuser = True
    admin.is_verified = True
    return admin


@pytest.fixture(scope="function")
def mock_test_link(mock_test_user):
    """Create a mock test link."""
    link_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    link = MagicMock()
    link.id = link_id
    link.short_code = "testcode"
    link.original_url = "https://example.com"
    link.user_id = mock_test_user.id
    link.created_at = now
    link.last_used_at = now
    link.expires_at = now + timedelta(days=7)
    link.visit_count = 0
    link.users = mock_test_user
    return link


@pytest.fixture(scope="function")
def mock_async_session():
    """Create a mock async session."""
    session = AsyncMock()
    # Setup mock methods commonly used in tests

    # For queries
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars().all.return_value = []

    session.execute.return_value = mock_result

    # For inserts/updates
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()

    return session


@pytest.fixture(scope="function")
def app(mock_async_session) -> FastAPI:
    """Create FastAPI app for testing."""
    app = main_app

    async def override_get_async_session():
        yield mock_async_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    return app


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """Create test client for FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_header(mock_test_user):
    """Create auth header for test user."""
    return {"Authorization": f"Bearer test_token_for_{mock_test_user.id}"}


@pytest.fixture
def admin_auth_header(mock_test_admin):
    """Create auth header for admin user."""
    return {"Authorization": f"Bearer test_token_for_{mock_test_admin.id}"}