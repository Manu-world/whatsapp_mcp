import pytest
from unittest.mock import patch, MagicMock
from app.service.twilio_service import send_whatsapp_message
from app.core.config import TWILIO_WHATSAPP_NUMBER

@pytest.fixture
def mock_twilio_client():
    with patch('app.service.twilio_service.twilio_client') as mock:
        yield mock

class TestTwilioService:
    def test_send_whatsapp_message_success(self, mock_twilio_client):
        # Setup
        test_to = "whatsapp:+1234567890"
        test_body = "Test message"
        mock_message = MagicMock()
        mock_twilio_client.messages.create.return_value = mock_message

        # Execute
        send_whatsapp_message(test_to, test_body)

        # Verify
        mock_twilio_client.messages.create.assert_called_once_with(
            body=test_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=test_to
        )

    def test_send_whatsapp_message_empty_body(self, mock_twilio_client):
        # Setup
        test_to = "whatsapp:+1234567890"
        test_body = ""
        mock_message = MagicMock()
        mock_twilio_client.messages.create.return_value = mock_message

        # Execute
        send_whatsapp_message(test_to, test_body)

        # Verify
        mock_twilio_client.messages.create.assert_called_once_with(
            body=test_body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=test_to
        )

    def test_send_whatsapp_message_invalid_number(self, mock_twilio_client):
        # Setup
        test_to = "invalid_number"
        test_body = "Test message"
        mock_twilio_client.messages.create.side_effect = Exception("Invalid number")

        # Execute and Verify
        with pytest.raises(Exception, match="Invalid number"):
            send_whatsapp_message(test_to, test_body)