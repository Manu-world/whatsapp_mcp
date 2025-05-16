import pytest
import httpx
from httpx import ASGITransport
from fastapi import status, FastAPI
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import root, webhook_router, lifespan  # Import the components directly


@pytest.mark.asyncio
async def test_root_redirects_to_docs():
    from app.main import app

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/docs"


@patch("app.main.init_agent", new_callable=AsyncMock)
@patch("app.main.close_agent", new_callable=AsyncMock)
def test_lifespan_hooks(mock_close_agent, mock_init_agent):
    # Reconstruct the FastAPI app using the real lifespan
    test_app = FastAPI(title="Test Bot", lifespan=lifespan)
    test_app.include_router(webhook_router)
    test_app.get("/")(root)

    # Using context manager triggers full lifespan (startup + shutdown)
    with TestClient(test_app, follow_redirects=False) as client:
        response = client.get("/")
        assert response.status_code == 307

    # Move assertions here — after TestClient context closes
    mock_init_agent.assert_awaited_once()
    mock_close_agent.assert_awaited_once()
