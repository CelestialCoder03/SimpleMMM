"""Integration test fixtures with real database sessions."""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.main import app
from app.models import User

# Use a separate test database URL (append _test if not already)
TEST_DATABASE_URL = settings.DATABASE_URL
if not TEST_DATABASE_URL.endswith("_test"):
    TEST_DATABASE_URL = TEST_DATABASE_URL + "_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def _db_is_reachable() -> bool:
    """Check if test database is reachable (sync probe)."""
    import asyncio

    async def _probe():
        try:
            async with test_engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return True
        except Exception:
            return False

    try:
        return asyncio.get_event_loop().run_until_complete(_probe())
    except Exception:
        try:
            return asyncio.run(_probe())
        except Exception:
            return False


# Skip entire module when DB is unavailable
pytestmark = pytest.mark.skipif(
    not _db_is_reachable(),
    reason="Test database not reachable",
)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def setup_database():
    """Create all tables once per test session, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user for authentication."""
    user = User(
        id=uuid4(),
        email=f"test-{uuid4().hex[:8]}@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def auth_token(test_user: User) -> str:
    """Create a valid JWT access token for the test user."""
    return create_access_token(subject=str(test_user.id))


@pytest_asyncio.fixture(loop_scope="session")
async def authenticated_client(
    db_session: AsyncSession,
    test_user: User,
    auth_token: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated async HTTP client."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_current_user() -> User:
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {auth_token}"},
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(loop_scope="session")
async def anonymous_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an unauthenticated async HTTP client with test DB."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client

    app.dependency_overrides.clear()
