"""WebSocket endpoint for live vessel updates."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting.

    Handles multiple client connections and provides methods for
    broadcasting updates to all connected clients.

    Attributes:
        active_connections: Set of currently connected WebSocket clients.
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: set[WebSocket] = set()
        self._subscriptions: dict[WebSocket, set[int]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection to accept.
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        self._subscriptions[websocket] = set()
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket.

        Args:
            websocket: WebSocket connection to remove.
        """
        self.active_connections.discard(websocket)
        self._subscriptions.pop(websocket, None)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    def subscribe(self, websocket: WebSocket, mmsi: int) -> None:
        """Subscribe a client to updates for a specific vessel.

        Args:
            websocket: Client connection.
            mmsi: Vessel MMSI to subscribe to.
        """
        if websocket in self._subscriptions:
            self._subscriptions[websocket].add(mmsi)

    def unsubscribe(self, websocket: WebSocket, mmsi: int) -> None:
        """Unsubscribe a client from vessel updates.

        Args:
            websocket: Client connection.
            mmsi: Vessel MMSI to unsubscribe from.
        """
        if websocket in self._subscriptions:
            self._subscriptions[websocket].discard(mmsi)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: Message dictionary to send.
        """
        if not self.active_connections:
            return

        data = json.dumps(message, default=str)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_vessel_update(self, vessel_data: dict[str, Any]) -> None:
        """Broadcast a vessel position update.

        Args:
            vessel_data: Vessel data dictionary with mmsi, lat, lon, etc.
        """
        message = {
            "type": "vessel_update",
            "data": vessel_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

    async def send_alert_created(self, alert_data: dict[str, Any]) -> None:
        """Broadcast a new alert notification.

        Args:
            alert_data: Alert data dictionary.
        """
        message = {
            "type": "alert_created",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)

    async def send_alert_resolved(self, alert_id: str) -> None:
        """Broadcast an alert resolution notification.

        Args:
            alert_id: ID of resolved alert.
        """
        message = {
            "type": "alert_resolved",
            "data": {"id": alert_id},
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connections for live updates.

    Accepts client connections and processes subscription messages.
    Runs until client disconnects.

    Args:
        websocket: WebSocket connection.
    """
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "subscribe" and "mmsi" in message:
                    manager.subscribe(websocket, message["mmsi"])
                elif action == "unsubscribe" and "mmsi" in message:
                    manager.unsubscribe(websocket, message["mmsi"])

            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from WebSocket client")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
