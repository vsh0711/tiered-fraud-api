import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_live_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # lifespan not auto-run with ASGITransport in all versions; hit live which is sync-safe
        res = await client.get("/v1/live")
        assert res.status_code == 200
        assert res.json()["status"] == "alive"


def test_plan_and_schemas_importable():
    from app.models.schemas import TransactionRequest

    req = TransactionRequest(
        request_id="t1",
        amount=10,
        merchant_category="grocery",
        country="US",
        device_risk_score=0.1,
        velocity_1h=0,
        velocity_24h=1,
    )
    assert req.country == "US"
