import os
import json
import pytest
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from urllib.parse import quote

from app.core import auth as auth_module
from app.api import auth as api_auth

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


def test_add_and_is_user_active(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not auth_module.is_user_active("123")
    auth_module.add_active_user("+123")
    assert auth_module.is_user_active("123")


def test_save_credentials_json_and_backup(tmp_path, monkeypatch):
    creds = DummyCreds()
    target = tmp_path / "token.json"
    auth_module.save_credentials_json(creds, str(target))
    assert json.loads(target.read_text()) == creds._data
    backup_dir = tmp_path / ".gmail-mcp"
    backup_file = backup_dir / auth_module.CREDENTIALS_FILENAME
    monkeypatch.setattr(auth_module, 'CREDENTIALS_BACKUP_DIR', str(backup_dir))
    monkeypatch.setattr(auth_module, 'CREDENTIALS_BACKUP_PATH', str(backup_file))
    auth_module.backup_credentials(creds)
    assert json.loads(backup_file.read_text()) == creds._data


def test_load_secrets(monkeypatch):
    class DummyClient:
        def get_secret_value(self, SecretId):
            return {"SecretString": json.dumps({"ENV_VARS": {"K":"V"}})}
    monkeypatch.setattr(auth_module, 'boto3', type('b', (), {'client': lambda *a, **k: DummyClient()}))
    res = auth_module.load_secrets()
    assert os.environ.get('K') == 'V'
    assert 'ENV_VARS' in res


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(api_auth.router, prefix="/api")
    return TestClient(app)

class DummyFlow:
    def __init__(self):
        self.credentials = DummyCreds()
    @classmethod
    def from_client_secrets_file(cls, *args, **kwargs):
        return cls()
    def authorization_url(self, **kwargs):
        return ("https://auth.url/", None)
    def fetch_token(self, code):
        self.credentials = DummyCreds(data={"token":"fetched"})

@pytest.fixture(autouse=True)
def patch_flow(monkeypatch):
    monkeypatch.setattr(api_auth.Flow, 'from_client_secrets_file', DummyFlow.from_client_secrets_file)


def test_auth_redirect(client):
    # Should redirect to the authorization URL with correct status without following redirects
    raw_resp = client.get(
        "/api/auth/redirect?user_number=12345&msg=hello world",
        follow_redirects=False
    )
    assert raw_resp.status_code == 307

@pytest.mark.parametrize("params,expected_status,expected_text", [
    ({}, 400, "Missing code or state"),
    ({"code":"c","state":"bad%7z"}, 400, "Invalid state format"),
])
def test_auth_callback_errors(client, params, expected_status, expected_text):
    url = "/api/auth/callback"
    if params:
        query = "?" + "&".join(f"{k}={v}" for k,v in params.items())
        url += query
    resp = client.get(url)
    assert resp.status_code == expected_status
    assert expected_text in resp.text


def test_auth_callback_success(client, monkeypatch):
    # Prepare valid state
    state = quote(json.dumps({"user_number":"123","msg":"hi"}))
    # Patch persistence and messaging
    called = {}
    monkeypatch.setattr(api_auth, 'save_user_credentials', lambda creds, user_number: called.setdefault('save_user', user_number))
    monkeypatch.setattr(api_auth, 'save_credentials_json', lambda creds, path: called.setdefault('save_json', path))
    monkeypatch.setattr(api_auth, 'backup_credentials', lambda creds: called.setdefault('backup', True))
    async def dummy_process(msg, thread_id):
        return "reply-msg"
    monkeypatch.setattr(api_auth, 'process_message', dummy_process)
    monkeypatch.setattr(api_auth, 'send_whatsapp_message', lambda to, body: called.setdefault('whatsapp', (to, body)))

    resp = client.get(f"/api/auth/callback?code=abc&state={state}")
    assert resp.status_code == 200
    assert "✅ You're authenticated" in resp.text
    # Verify side-effects
    assert called['save_user'] == '123'
    assert called['save_json'] == 'credentials.json'
    assert called['backup'] is True
    assert called['whatsapp'] == ('whatsapp:+123', 'reply-msg')
