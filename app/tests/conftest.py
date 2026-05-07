import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.database import create_all_for_tests, reset_engine_for_tests
from src.main import app


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "clearpath-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("GHL_WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()
    await reset_engine_for_tests()
    await create_all_for_tests()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client

    await reset_engine_for_tests()
    get_settings.cache_clear()
