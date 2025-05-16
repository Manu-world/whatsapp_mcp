import pytest
from unittest.mock import Mock, patch
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

@pytest.fixture
def mock_credentials():
    """Mock Google OAuth2 credentials"""
    return Mock(spec=Credentials)

@pytest.fixture
def mock_drive_service(mock_credentials):
    """Mock Google Drive service"""
    with patch('app.core.auth.get_drive_service') as mock_service:
        mock_drive = Mock()
        mock_service.return_value = mock_drive
        yield mock_drive