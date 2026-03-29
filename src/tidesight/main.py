"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from tidesight import __version__
from tidesight.api.routes import router
from tidesight.api.websocket import websocket_endpoint
from tidesight.background import start_background_tasks
from tidesight.db.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Initializes database and starts background tasks on startup.
    """
    await init_db()
    await start_background_tasks()
    logger.info("Tidesight started")
    yield
    logger.info("Tidesight shutting down")


app = FastAPI(
    title="Tidesight",
    description="Large vessel arrival prediction for Port of Rotterdam",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    """WebSocket endpoint for live vessel updates."""
    await websocket_endpoint(websocket)
