import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import patch, MagicMock
from app.api.webhook import router, ChatRequest
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

client = TestClient(app)

@pytest.fixture
def mock_process_message():
    with patch('app.api.webhook.process_message') as mock:
        yield mock

@pytest.fixture
def mock_send_whatsapp_message():
    with patch('app.api.webhook.send_whatsapp_message') as mock:
        yield mock

@pytest.fixture
def mock_check_and_clean_files():
    with patch('app.api.webhook.check_and_clean_files') as mock:
        mock.return_value = True
        yield mock

class TestWebhookEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert (datetime.now() - timestamp).total_seconds() < 60

    def test_webhook_endpoint(self, mock_process_message, mock_send_whatsapp_message, mock_check_and_clean_files):
        test_message = "Hello, world!"
        test_sender = "whatsapp:+1234567890"
        today_date = datetime.now().strftime("%Y-%m-%d")
        expected_thread_id = f"+1234567890_{today_date}"
        expected_response = "This is a test response"

        # Configure mocks
        mock_process_message.return_value = expected_response
        mock_send_whatsapp_message.return_value = None

        response = client.post(
            "/webhook",
            data={"From": test_sender, "Body": test_message},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        assert response.text == ""

        # Verify mocks were called correctly
        mock_process_message.assert_called_once_with(test_message, expected_thread_id)
        mock_send_whatsapp_message.assert_called_once_with(test_sender, expected_response)

    def test_webhook_missing_parameters(self):
        response = client.post(
            "/webhook",
            data={},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422  # Unprocessable Entity

    def test_chat_endpoint(self, mock_process_message):
        test_message = "API test message"
        test_thread_id = "test_thread_123"
        expected_response = "API test response"

        # Configure mock
        mock_process_message.return_value = expected_response

        response = client.post(
            "/chat",
            json={"message": test_message, "thread_id": test_thread_id}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == expected_response
        assert data["thread_id"] == test_thread_id

        # Verify mock was called correctly
        mock_process_message.assert_called_once_with(test_message, test_thread_id)

    def test_chat_endpoint_no_thread_id(self, mock_process_message):
        test_message = "Message without thread"
        expected_response = "Response without thread"

        # Configure mock
        mock_process_message.return_value = expected_response

        response = client.post(
            "/chat",
            json={"message": test_message}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == expected_response
        assert data["thread_id"] is None

        # Verify mock was called correctly
        mock_process_message.assert_called_once_with(test_message, None)

    def test_chat_endpoint_invalid_request(self):
        response = client.post(
            "/chat",
            json={"invalid": "request"}
        )
        assert response.status_code == 422  # Unprocessable Entity

    @patch('app.api.webhook.datetime.datetime')
    def test_webhook_thread_id_format(self, mock_datetime, mock_process_message, mock_send_whatsapp_message, mock_check_and_clean_files):
        # Test thread ID generation with specific date
        test_message = "Date test"
        test_sender = "whatsapp:+1234567890"

        fixed_date = datetime(2023, 1, 1)

        # Configure the mock to return our fixed date
        mock_datetime.now.return_value = fixed_date

        expected_thread_id = f"+1234567890_2023-01-01"
        expected_response = "Date test response"

        mock_process_message.return_value = expected_response
        mock_send_whatsapp_message.return_value = None

        response = client.post(
            "/webhook",
            data={"From": test_sender, "Body": test_message},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Verify thread ID format
        mock_process_message.assert_called_once_with(test_message, expected_thread_id)
        assert response.status_code == 200
