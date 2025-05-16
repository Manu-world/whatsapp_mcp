import os
import json
import pytest
import logging
from pathlib import Path
from unittest.mock import MagicMock
import builtins

from app.core import auth as auth_module


class DummyCreds:
    def __init__(self, valid=True, expired=False, refresh_token=None, data=None):
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self._data = data or {"token": "abc"}

    def to_json(self):
        return json.dumps(self._data)

    @classmethod
    def from_authorized_user_info(cls, info, scopes):
        return DummyCreds(valid=True, data=info)

    def refresh(self, request):
        self.valid = True


@pytest.fixture(autouse=True)
def disable_logging(monkeypatch):
    monkeypatch.setenv('ENVIRONMENT', 'development')
    logging.getLogger().setLevel(logging.CRITICAL)
    yield


def test_is_production_environment_default(monkeypatch):
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    assert not auth_module.is_production_environment()

    monkeypatch.setenv('ENVIRONMENT', 'production')
    assert auth_module.is_production_environment()

    monkeypatch.setenv('ENVIRONMENT', 'Production')
    assert auth_module.is_production_environment()


def test_add_and_is_user_active(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    user_file = tmp_path / "active_user.txt"

    assert not auth_module.is_user_active("123")

    auth_module.add_active_user("+123")
    assert user_file.exists()
    assert auth_module.is_user_active("123")

    auth_module.add_active_user("123")
    lines = user_file.read_text().splitlines()
    assert lines == ["123"]


def test_add_active_user_failure(monkeypatch, caplog):
    monkeypatch.setattr(builtins, 'open', lambda *a, **kw: (_ for _ in ()).throw(OSError("Disk full")))
    caplog.set_level(logging.ERROR)
    auth_module.add_active_user("999")
    assert "Failed to add active user 999: Disk full" in caplog.text


def test_save_credentials_json_and_backup(tmp_path, monkeypatch):
    creds = DummyCreds(valid=True)
    target = tmp_path / "token.json"
    auth_module.save_credentials_json(creds, str(target))
    assert target.exists()
    assert json.loads(target.read_text()) == creds._data

    backup_dir = tmp_path / ".gmail-mcp"
    backup_file = backup_dir / auth_module.CREDENTIALS_FILENAME
    monkeypatch.setattr(auth_module, 'CREDENTIALS_BACKUP_DIR', str(backup_dir))
    monkeypatch.setattr(auth_module, 'CREDENTIALS_BACKUP_PATH', str(backup_file))

    auth_module.backup_credentials(creds)
    assert backup_file.exists()
    assert json.loads(backup_file.read_text()) == creds._data


def test_save_user_credentials(monkeypatch):
    dummy_creds = DummyCreds()
    called = {}

    def fake_add_active(user_number):
        called['number'] = user_number

    monkeypatch.setattr(auth_module, "add_active_user", fake_add_active)
    auth_module.save_user_credentials(dummy_creds, user_number="789")
    assert called['number'] == "789"


def test_load_secrets_success(monkeypatch):
    class DummyClient:
        def get_secret_value(self, SecretId):
            return {"SecretString": json.dumps({"ENV_VARS": {"TEST_KEY": "VALUE"}})}

    monkeypatch.setattr(auth_module, 'boto3', type('b', (), {'client': lambda *args, **kwargs: DummyClient()}))
    secrets = auth_module.load_secrets()
    assert os.environ.get('TEST_KEY') == 'VALUE'
    assert 'ENV_VARS' in secrets


def test_load_secrets_failure(monkeypatch, caplog):
    monkeypatch.setattr(auth_module, 'boto3', type('b', (), {'client': lambda *args, **kwargs: (_ for _ in ()).throw(Exception("aws failure"))}))
    caplog.set_level(logging.WARNING)
    result = auth_module.load_secrets()
    assert result is None
    assert "Failed to load secrets" in caplog.text


def test_get_drive_service_fallback(monkeypatch):
    monkeypatch.setattr(auth_module, "get_production_drive_service", lambda _: (_ for _ in ()).throw(Exception("fail")))
    mock_local = MagicMock()
    monkeypatch.setattr(auth_module, "get_local_drive_service", lambda _: mock_local)
    service = auth_module.get_drive_service("999")
    assert service == mock_local


def test_get_drive_service_all_fail(monkeypatch):
    monkeypatch.setattr(auth_module, "get_production_drive_service", lambda _: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr(auth_module, "get_local_drive_service", lambda _: (_ for _ in ()).throw(Exception("fail too")))
    with pytest.raises(Exception, match="All authentication methods failed"):
        auth_module.get_drive_service()


def test_get_production_drive_service_refresh(monkeypatch):
    dummy_token = {"token": "abc", "refresh_token": "refresh", "expired": True}
    dummy_creds = DummyCreds(valid=False, expired=True, refresh_token="refresh", data=dummy_token)

    monkeypatch.setattr(auth_module, "load_secrets", lambda: {
        "token_json": json.dumps(dummy_token),
        "credentials_json": dummy_token
    })
    monkeypatch.setattr(auth_module.Credentials, 'from_authorized_user_info', lambda info, scopes: dummy_creds)
    monkeypatch.setattr(auth_module, "build", lambda *a, **kw: "mock_drive")
    monkeypatch.setattr(auth_module, "save_credentials_json", lambda *a, **kw: None)
    monkeypatch.setattr(auth_module, "save_user_credentials", lambda *a, **kw: None)
    monkeypatch.setattr(auth_module, "backup_credentials", lambda *a, **kw: None)
    monkeypatch.setattr(auth_module, "boto3", MagicMock(client=lambda *a, **kw: MagicMock(update_secret=lambda **kwargs: None)))

    service = auth_module.get_production_drive_service("123")
    assert service == "mock_drive"


def test_get_production_drive_service_needs_flow(monkeypatch):
    monkeypatch.setattr(auth_module, "load_secrets", lambda: {
        "credentials_json": {"client_id": "123"}
    })

    mock_creds = DummyCreds(valid=True)
    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds
    monkeypatch.setattr(auth_module, "InstalledAppFlow", MagicMock(from_client_secrets_file=lambda f, scopes: mock_flow))
    monkeypatch.setattr(auth_module, "build", lambda *a, **kw: "mock_drive")

    monkeypatch.setattr(auth_module, "save_credentials_json", lambda *a, **kw: None)
    monkeypatch.setattr(auth_module, "save_user_credentials", lambda *a, **kw: None)
    monkeypatch.setattr(auth_module, "backup_credentials", lambda *a, **kw: None)
    monkeypatch.setattr(auth_module, "boto3", MagicMock(client=lambda *a, **kw: MagicMock(update_secret=lambda **kwargs: None)))

    service = auth_module.get_production_drive_service("123")
    assert service == "mock_drive"


def test_get_local_drive_service_file_not_found(monkeypatch):
    monkeypatch.setattr(auth_module.os.path, "exists", lambda path: False)
    with pytest.raises(FileNotFoundError, match="Missing 'gcp-oauth.keys.json' for local auth."):
        auth_module.get_local_drive_service("123")
