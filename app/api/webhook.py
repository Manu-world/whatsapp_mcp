# app/api/webhook.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from app.core.agent_service import process_message
from app.core.config import GOAUTH_REDIRECT_URL
from app.service.twilio_service import send_whatsapp_message
from app.utils.sys_path_fixer import check_and_clean_files
import datetime
import urllib.parse
import json
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

router = APIRouter()

@router.get("/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.datetime.now().isoformat()
    })

@router.post("/webhook")
async def webhook(request: Request, From: str = Form(...), Body: str = Form(...)):
    sender = From.replace("whatsapp:", "")
    incoming_msg = Body
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    thread_id = f"{sender}_{today_date}"

    # Check auth first
    print("sender:", sender)
    is_authenticated = check_and_clean_files(user_number=sender)
    print(is_authenticated, ":is authenticated")

    if not is_authenticated:
        # Send them a WhatsApp link to authenticate via redirect
        auth_url = (
            f"{GOAUTH_REDIRECT_URL}/api/auth/redirect"
            f"?user_number={sender}&msg={urllib.parse.quote(incoming_msg)}"
        )
        send_whatsapp_message(From, f"🔒 Please authenticate to continue: {auth_url}")

        return Response(status_code=200)

    # Otherwise, continue processing the message
    response_msg = await process_message(incoming_msg, thread_id)
    send_whatsapp_message(From, response_msg)
    return Response(status_code=200)


@router.post("/chat")
async def chat(request: ChatRequest):
    response_msg = await process_message(request.message, request.thread_id)
    return JSONResponse({
        "response": response_msg,
        "thread_id": request.thread_id
    })
