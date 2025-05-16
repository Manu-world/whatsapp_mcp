from app.core.config import twilio_client, TWILIO_WHATSAPP_NUMBER

def send_whatsapp_message(to: str, body: str):
    twilio_client.messages.create(
        body=body,
        from_=TWILIO_WHATSAPP_NUMBER,
        to=to
    )
