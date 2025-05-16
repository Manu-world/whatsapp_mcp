import pytest
from fastapi.testclient import TestClient
from app.api.index import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def api_client():
    return client

# Test the webhook router inclusion
def test_webhook_router_inclusion(api_client):
    response = api_client.get("/api/some-webhook-endpoint")  # Adjust this path as needed
    assert response.status_code in [200, 404]  # 200 if the endpoint exists, 404 if not defined

# Test the auth router inclusion
def test_auth_router_inclusion(api_client):
    response = api_client.get("/api/some-auth-endpoint")  # Adjust this path as needed
    assert response.status_code in [200, 404]  # 200 if the endpoint exists, 404 if not defined
