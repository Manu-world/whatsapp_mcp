# app/api/auth.py
import datetime
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from app.core.agent_service import process_message
from app.core.auth import backup_credentials, save_credentials_json, save_user_credentials
import os
import urllib.parse
import json

from app.core.config import GOAUTH_REDIRECT_URL
from app.service.twilio_service import send_whatsapp_message

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://mail.google.com/"
]


@router.get("/auth/redirect")
async def auth_redirect(user_number: str, msg: str = ""):
    flow = Flow.from_client_secrets_file(
        'gcp-oauth.keys.json',
        scopes=SCOPES,
        redirect_uri=f"{GOAUTH_REDIRECT_URL}/api/auth/callback"
    )

    # Safely encode state as JSON
    state_payload = json.dumps({
        "user_number": user_number,
        "msg": msg
    })
    encoded_state = urllib.parse.quote(state_payload)

    auth_url, _ = flow.authorization_url(
        prompt='consent',
        access_type='offline',
        state=encoded_state
    )
    return RedirectResponse(auth_url)

@router.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    raw_state = request.query_params.get("state")

    if not code or not raw_state:
        return HTMLResponse("<h1>Something went wrong. Missing code or state.</h1>", status_code=400)

    try:
        decoded_state = json.loads(urllib.parse.unquote(raw_state))
        user_number = decoded_state.get("user_number")
        msg = decoded_state.get("msg")
    except Exception as e:
        return HTMLResponse(f"<h1>Invalid state format: {e}</h1>", status_code=400)

    flow = Flow.from_client_secrets_file(
        'gcp-oauth.keys.json',
        scopes=SCOPES,
        redirect_uri=f"{GOAUTH_REDIRECT_URL}/api/auth/callback"
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    save_user_credentials(creds, user_number=user_number)
    save_credentials_json(creds, "credentials.json")
    backup_credentials(creds)

    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    thread_id = f"{user_number}_{today_date}"
    response_msg = await process_message(msg, thread_id)

    send_whatsapp_message(to=f"whatsapp:+{user_number.strip()}", body=response_msg)

    return HTMLResponse("<h2>✅ You're authenticated! Go back to WhatsApp and continue your chat.</h2>")
