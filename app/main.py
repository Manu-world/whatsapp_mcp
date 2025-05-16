from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from app.api.index import router as webhook_router
from app.core.agent_service import init_agent, close_agent
from app.core.config import setup_logging
import os
import pathlib

logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create .gmail-mcp directory in home directory
    home_dir = str(pathlib.Path.home())
    gmail_mcp_dir = os.path.join(home_dir, '.gmail-mcp')
    os.makedirs(gmail_mcp_dir, exist_ok=True)
    logger.info(f"Created .gmail-mcp directory at {gmail_mcp_dir}")

    logger.info("Initializing agent")
    await init_agent()
    logger.info("Agent initialized.")
    yield
    logger.info("Closing agent...")
    await close_agent()
    logger.info("Agent closed successfully.")

app = FastAPI(title="WhatsApp MCP Bot", lifespan=lifespan)

app.include_router(webhook_router)

@app.get("/")
def root():
    return RedirectResponse(url="/docs")
