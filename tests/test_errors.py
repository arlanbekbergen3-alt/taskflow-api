import logging

import pytest
from httpx import AsyncClient, ASGITransport

from core.auth import get_current_user
from main import app


def broken_dependency():
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_and_is_logged_once(caplog):
    app.dependency_overrides[get_current_user] = broken_dependency
    try:
        # raise_app_exceptions=True (the default) would fail this test
        # if the exception escaped the middleware instead of stopping there.
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            with caplog.at_level(logging.ERROR):
                response = await client.get("/auth/me")
    finally:
        del app.dependency_overrides[get_current_user]

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}

    records = [r for r in caplog.records if r.exc_info]
    assert len(records) == 1
    assert records[0].getMessage() == "Unhandled exception on GET /auth/me"
    assert isinstance(records[0].exc_info[1], RuntimeError)
