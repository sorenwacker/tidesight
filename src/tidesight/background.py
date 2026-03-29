"""Background tasks for AIS ingestion and data processing."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from tidesight.api.websocket import manager
from tidesight.config import settings
from tidesight.db.database import async_session_maker
from tidesight.models import Vessel, VesselPosition
from tidesight.services.ais_client import AISClient, AISMessage, AISMessageType
from tidesight.services.predictor import (
    calculate_distance_to_entry,
    calculate_eta,
    find_target_window,
    is_heading_towards_entry,
    is_large_vessel,
)
from tidesight.services.tide_service import TideService

logger = logging.getLogger(__name__)

# Cache to throttle updates per vessel (mmsi -> last_broadcast_time)
_broadcast_cache: dict[int, datetime] = {}
BROADCAST_INTERVAL = timedelta(seconds=5)

# Cache to throttle position saves (mmsi -> last_save_time)
_position_cache: dict[int, datetime] = {}
POSITION_SAVE_INTERVAL = timedelta(seconds=30)

# Cache for tidal windows (refreshed periodically)
_tidal_windows: list[dict[str, Any]] = []


async def handle_ais_message(message: AISMessage) -> None:
    """Process incoming AIS message and update database.

    Args:
        message: Parsed AIS message.
    """
    now = datetime.now(timezone.utc)

    async with async_session_maker() as session:
        # Get or create vessel
        result = await session.execute(
            select(Vessel).where(Vessel.mmsi == message.mmsi)
        )
        vessel = result.scalar_one_or_none()

        if vessel is None:
            vessel = Vessel(mmsi=message.mmsi, lat=0.0, lon=0.0)
            session.add(vessel)

        # Update vessel based on message type
        if message.message_type == AISMessageType.POSITION_REPORT:
            vessel.lat = message.data["lat"]
            vessel.lon = message.data["lon"]
            vessel.speed_knots = message.data.get("speed_knots", 0.0)
            vessel.heading = message.data.get("heading")
            vessel.cog = message.data.get("cog")
            vessel.updated_at = now

            # Calculate ETA only if moving towards Hoek van Holland
            if vessel.speed_knots > 0.5 and is_heading_towards_entry(
                vessel.lat, vessel.lon, vessel.cog
            ):
                vessel.eta = calculate_eta(
                    vessel.lat, vessel.lon, vessel.speed_knots
                )
                # For large vessels, find target tidal window
                if vessel.is_large and vessel.eta and _tidal_windows:
                    target = find_target_window(vessel.eta, _tidal_windows)
                    if target:
                        vessel.target_window = target["peak_time"]
            else:
                # Clear ETA if not heading towards entry
                vessel.eta = None
                vessel.target_window = None

            # Save position history (throttled)
            last_save = _position_cache.get(message.mmsi)
            if last_save is None or (now - last_save) >= POSITION_SAVE_INTERVAL:
                position = VesselPosition(
                    mmsi=message.mmsi,
                    lat=vessel.lat,
                    lon=vessel.lon,
                    speed_knots=vessel.speed_knots,
                    heading=vessel.heading,
                    timestamp=now,
                )
                session.add(position)
                _position_cache[message.mmsi] = now

        elif message.message_type == AISMessageType.SHIP_STATIC_DATA:
            vessel.name = message.data.get("name") or vessel.name
            vessel.loa_m = message.data.get("loa_m") or vessel.loa_m
            vessel.beam_m = message.data.get("beam_m") or vessel.beam_m
            vessel.draft_m = message.data.get("draft_m") or vessel.draft_m

            # Update large vessel status
            vessel.is_large = is_large_vessel(vessel.draft_m, vessel.loa_m)

        await session.commit()

        # Throttle WebSocket broadcasts
        last_broadcast = _broadcast_cache.get(message.mmsi)
        if last_broadcast is None or (now - last_broadcast) >= BROADCAST_INTERVAL:
            distance = calculate_distance_to_entry(vessel.lat, vessel.lon)
            await manager.send_vessel_update({
                "mmsi": vessel.mmsi,
                "name": vessel.name,
                "lat": vessel.lat,
                "lon": vessel.lon,
                "speed_knots": vessel.speed_knots,
                "heading": vessel.heading,
                "cog": vessel.cog,
                "draft_m": vessel.draft_m,
                "loa_m": vessel.loa_m,
                "beam_m": vessel.beam_m,
                "is_large": vessel.is_large,
                "eta": vessel.eta.isoformat() if vessel.eta else None,
                "target_window": vessel.target_window.isoformat() if vessel.target_window else None,
                "distance_km": distance,
            })
            _broadcast_cache[message.mmsi] = now


async def run_ais_client() -> None:
    """Run AIS client in background."""
    if not settings.ais_api_key:
        logger.warning("AIS API key not set, skipping AIS client")
        return

    client = AISClient()
    client.add_handler(handle_ais_message)

    logger.info("Starting AIS client...")
    await client.connect()


async def run_tide_refresh() -> None:
    """Periodically refresh tidal data and cache windows."""
    global _tidal_windows
    service = TideService()

    while True:
        try:
            logger.info("Refreshing tidal data...")
            predictions, high_tides = await service.fetch_predictions()
            _tidal_windows = high_tides
            logger.info(f"Fetched {len(predictions)} predictions, {len(high_tides)} high tides")
        except Exception as e:
            logger.error(f"Failed to refresh tides: {e}")

        await asyncio.sleep(settings.tide_refresh_minutes * 60)


async def start_background_tasks() -> None:
    """Start all background tasks."""
    asyncio.create_task(run_ais_client())
    asyncio.create_task(run_tide_refresh())
