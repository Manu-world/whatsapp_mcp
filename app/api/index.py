# app/main.py or wherever you're setting up the app
from fastapi import APIRouter
from app.api import webhook, auth

router = APIRouter()

router.include_router(webhook.router, prefix="/api")
router.include_router(auth.router, prefix="/api")
