"""AIS client for aisstream.io WebSocket connection."""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Coroutine

import websockets
from websockets.exceptions import ConnectionClosed

from tidesight.config import settings

logger = logging.getLogger(__name__)


class AISMessageType(str, Enum):
    """Types of AIS messages we process."""

    POSITION_REPORT = "PositionReport"
    SHIP_STATIC_DATA = "ShipStaticData"


@dataclass
class AISMessage:
    """Parsed AIS message with type and data.

    Attributes:
        message_type: Type of AIS message.
        mmsi: Maritime Mobile Service Identity.
        data: Parsed message data dictionary.
    """

    message_type: AISMessageType
    mmsi: int
    data: dict[str, Any]


def parse_position_report(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Parse an AIS position report message.

    Args:
        raw: Raw AIS message dictionary.

    Returns:
        Parsed position data or None if invalid.
    """
    try:
        meta = raw.get("MetaData", {})
        message = raw.get("Message", {}).get("PositionReport", {})

        mmsi = meta.get("MMSI")
        lat = message.get("Latitude")
        lon = message.get("Longitude")

        # Validate coordinates
        if lat is None or lon is None:
            return None
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None

        # Parse heading - 511 means not available
        heading = message.get("TrueHeading")
        if heading == 511:
            heading = None

        return {
            "mmsi": mmsi,
            "lat": lat,
            "lon": lon,
            "speed_knots": message.get("Sog", 0.0),
            "heading": heading,
            "cog": message.get("Cog"),
        }
    except (KeyError, TypeError):
        return None


def parse_ship_static_data(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Parse an AIS ship static data message.

    Extracts vessel name and dimensions from static data message.
    Dimensions are converted from decimeters to meters.

    Args:
        raw: Raw AIS message dictionary.

    Returns:
        Parsed static data or None if invalid.
    """
    try:
        meta = raw.get("MetaData", {})
        message = raw.get("Message", {}).get("ShipStaticData", {})

        mmsi = meta.get("MMSI")
        if mmsi is None:
            return None

        name = message.get("Name", "").strip()
        dimensions = message.get("Dimension", {})

        # Calculate LOA (A + B) and beam (C + D)
        a = dimensions.get("A", 0) or 0
        b = dimensions.get("B", 0) or 0
        c = dimensions.get("C", 0) or 0
        d = dimensions.get("D", 0) or 0

        loa_m = float(a + b) if (a + b) > 0 else None
        beam_m = float(c + d) if (c + d) > 0 else None

        # Draft is in decimeters
        draft_dm = message.get("MaximumStaticDraught")
        draft_m = draft_dm / 10.0 if draft_dm else None

        return {
            "mmsi": mmsi,
            "name": name if name else None,
            "loa_m": loa_m,
            "beam_m": beam_m,
            "draft_m": draft_m,
        }
    except (KeyError, TypeError):
        return None


def parse_ais_message(raw: dict[str, Any]) -> AISMessage | None:
    """Parse a raw AIS message into structured format.

    Args:
        raw: Raw AIS message dictionary from WebSocket.

    Returns:
        Parsed AISMessage or None if message type unknown or invalid.
    """
    message_type = raw.get("MessageType")

    if message_type == AISMessageType.POSITION_REPORT.value:
        data = parse_position_report(raw)
        if data:
            return AISMessage(
                message_type=AISMessageType.POSITION_REPORT,
                mmsi=data["mmsi"],
                data=data,
            )

    elif message_type == AISMessageType.SHIP_STATIC_DATA.value:
        data = parse_ship_static_data(raw)
        if data:
            return AISMessage(
                message_type=AISMessageType.SHIP_STATIC_DATA,
                mmsi=data["mmsi"],
                data=data,
            )

    return None


MessageHandler = Callable[[AISMessage], Coroutine[Any, Any, None]]


class AISClient:
    """WebSocket client for aisstream.io AIS data stream.

    Maintains persistent connection with automatic reconnection.
    Filters messages by bounding box and dispatches to handlers.

    Attributes:
        api_key: aisstream.io API key.
        ws_url: WebSocket URL for AIS stream.
        bounding_box: Geographic filter as [[lat_min, lon_min], [lat_max, lon_max]].
        handlers: List of async functions to call for each message.
    """

    def __init__(
        self,
        api_key: str | None = None,
        ws_url: str | None = None,
        bounding_box: list[list[float]] | None = None,
    ) -> None:
        """Initialize AIS client.

        Args:
            api_key: Override API key (default from settings).
            ws_url: Override WebSocket URL (default from settings).
            bounding_box: Override bounding box (default from settings).
        """
        self.api_key = api_key or settings.ais_api_key
        self.ws_url = ws_url or settings.ais_ws_url
        self.bounding_box = bounding_box or settings.ais_bounding_box
        self.handlers: list[MessageHandler] = []
        self._running = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    def add_handler(self, handler: MessageHandler) -> None:
        """Register a message handler.

        Args:
            handler: Async function called for each parsed message.
        """
        self.handlers.append(handler)

    def _build_subscription(self) -> dict[str, Any]:
        """Build subscription message for aisstream.io.

        Returns:
            Subscription message dictionary.
        """
        return {
            "APIKey": self.api_key,
            "BoundingBoxes": [self.bounding_box],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
        }

    async def _dispatch_message(self, message: AISMessage) -> None:
        """Dispatch message to all registered handlers.

        Args:
            message: Parsed AIS message.
        """
        for handler in self.handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    async def _process_messages(self, websocket: Any) -> None:
        """Process incoming WebSocket messages.

        Args:
            websocket: Active WebSocket connection.
        """
        async for raw_data in websocket:
            try:
                raw_message = json.loads(raw_data)
                message = parse_ais_message(raw_message)
                if message:
                    await self._dispatch_message(message)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from AIS stream")

    async def connect(self) -> None:
        """Connect to AIS stream and process messages.

        Maintains connection with automatic reconnection on failure.
        Call stop() to terminate the connection loop.
        """
        self._running = True
        self._reconnect_delay = 1.0

        while self._running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    # Send subscription
                    subscription = self._build_subscription()
                    await websocket.send(json.dumps(subscription))
                    logger.info("Connected to AIS stream")

                    # Reset delay on successful connection
                    self._reconnect_delay = 1.0

                    # Process messages
                    await self._process_messages(websocket)

            except ConnectionClosed:
                logger.warning("AIS stream connection closed")
            except Exception as e:
                logger.error(f"AIS stream error: {e}")

            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay,
                )

    def stop(self) -> None:
        """Stop the connection loop."""
        self._running = False
