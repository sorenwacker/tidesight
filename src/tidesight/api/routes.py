"""FastAPI REST API routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tidesight import __version__
from tidesight.api.schemas import (
    AlertListResponse,
    AlertResponse,
    ErrorWrapper,
    HealthResponse,
    HighTideWindowResponse,
    TidePredictionResponse,
    TideResponse,
    VesselListResponse,
    VesselResponse,
)
from tidesight.db.database import get_session
from tidesight.models import Alert, Vessel, VesselPosition
from tidesight.services.predictor import calculate_distance_to_entry
from tidesight.services.tide_service import TideService

router = APIRouter(prefix="/api")


class PositionPoint(BaseModel):
    """Single position in trajectory."""

    lat: float
    lon: float
    speed_knots: float
    heading: float | None
    cog: float | None
    timestamp: datetime


class TrajectoryResponse(BaseModel):
    """Vessel trajectory response."""

    mmsi: int
    name: str | None
    positions: list[PositionPoint]


class ReplayFrame(BaseModel):
    """Single frame of replay data containing all vessel positions at a timestamp."""

    timestamp: datetime
    vessels: list[dict]


class ReplayResponse(BaseModel):
    """Replay data response."""

    start_time: datetime
    end_time: datetime
    frame_count: int
    frames: list[ReplayFrame]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    return HealthResponse(status="ok", version=__version__)


@router.get(
    "/vessels",
    response_model=VesselListResponse,
    responses={500: {"model": ErrorWrapper}},
)
async def list_vessels(
    large_only: bool = Query(False, description="Filter to large vessels only"),
    name: str | None = Query(None, description="Filter by vessel name (partial match)"),
    min_speed: float | None = Query(None, description="Minimum speed in knots"),
    max_distance: float | None = Query(None, description="Maximum distance from entry in nm"),
    max_age_minutes: int = Query(30, description="Max age of last update in minutes"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
) -> VesselListResponse:
    """List all tracked vessels with filters.

    Args:
        large_only: If True, only return large (tide-bound) vessels.
        name: Filter by vessel name (case-insensitive partial match).
        min_speed: Only return vessels moving faster than this speed.
        max_distance: Only return vessels within this distance from entry.
        max_age_minutes: Only return vessels updated within this many minutes.
        limit: Maximum number of vessels to return.
        session: Database session.

    Returns:
        List of vessel data.
    """
    # Only show vessels updated within max_age_minutes, with valid coordinates
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    query = (
        select(Vessel)
        .where(Vessel.updated_at >= cutoff)
        .where(Vessel.lat != 0.0)
        .where(Vessel.lon != 0.0)
        .order_by(Vessel.updated_at.desc())
        .limit(limit)
    )

    if large_only:
        query = query.where(Vessel.is_large == True)  # noqa: E712

    if name:
        query = query.where(Vessel.name.ilike(f"%{name}%"))

    if min_speed is not None:
        query = query.where(Vessel.speed_knots >= min_speed)

    result = await session.execute(query)
    vessels = result.scalars().all()

    vessel_responses = []
    for v in vessels:
        distance = calculate_distance_to_entry(v.lat, v.lon) if v.lat and v.lon else None

        # Apply distance filter (post-query since it's calculated)
        if max_distance is not None and distance is not None and distance > max_distance:
            continue

        vessel_responses.append(
            VesselResponse(
                mmsi=v.mmsi,
                name=v.name,
                lat=v.lat,
                lon=v.lon,
                speed_knots=v.speed_knots,
                heading=v.heading,
                draft_m=v.draft_m,
                loa_m=v.loa_m,
                beam_m=v.beam_m,
                is_large=v.is_large,
                eta=v.eta,
                target_window=v.target_window,
                distance_km=distance,
                updated_at=v.updated_at,
            )
        )

    return VesselListResponse(vessels=vessel_responses)


@router.get(
    "/vessels/{mmsi}",
    response_model=VesselResponse,
    responses={404: {"model": ErrorWrapper}},
)
async def get_vessel(
    mmsi: int,
    session: AsyncSession = Depends(get_session),
) -> VesselResponse:
    """Get details for a specific vessel.

    Args:
        mmsi: Maritime Mobile Service Identity.
        session: Database session.

    Returns:
        Vessel details.

    Raises:
        HTTPException: If vessel not found.
    """
    result = await session.execute(select(Vessel).where(Vessel.mmsi == mmsi))
    vessel = result.scalar_one_or_none()

    if not vessel:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Vessel {mmsi} not found"}},
        )

    distance = calculate_distance_to_entry(vessel.lat, vessel.lon)

    return VesselResponse(
        mmsi=vessel.mmsi,
        name=vessel.name,
        lat=vessel.lat,
        lon=vessel.lon,
        speed_knots=vessel.speed_knots,
        heading=vessel.heading,
        draft_m=vessel.draft_m,
        loa_m=vessel.loa_m,
        beam_m=vessel.beam_m,
        is_large=vessel.is_large,
        eta=vessel.eta,
        target_window=vessel.target_window,
        distance_km=distance,
        updated_at=vessel.updated_at,
    )


@router.get(
    "/vessels/{mmsi}/trajectory",
    response_model=TrajectoryResponse,
    responses={404: {"model": ErrorWrapper}},
)
async def get_vessel_trajectory(
    mmsi: int,
    hours: int = Query(6, ge=1, le=48, description="Hours of history"),
    session: AsyncSession = Depends(get_session),
) -> TrajectoryResponse:
    """Get position history for a vessel to draw trajectory.

    Args:
        mmsi: Maritime Mobile Service Identity.
        hours: Number of hours of history to return.
        session: Database session.

    Returns:
        List of historical positions.

    Raises:
        HTTPException: If vessel not found.
    """
    # Get vessel info
    vessel_result = await session.execute(select(Vessel).where(Vessel.mmsi == mmsi))
    vessel = vessel_result.scalar_one_or_none()

    if not vessel:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": f"Vessel {mmsi} not found"}},
        )

    # Get position history
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    pos_query = (
        select(VesselPosition)
        .where(VesselPosition.mmsi == mmsi)
        .where(VesselPosition.timestamp >= since)
        .order_by(VesselPosition.timestamp)
    )
    pos_result = await session.execute(pos_query)
    positions = pos_result.scalars().all()

    return TrajectoryResponse(
        mmsi=mmsi,
        name=vessel.name,
        positions=[
            PositionPoint(
                lat=p.lat,
                lon=p.lon,
                speed_knots=p.speed_knots,
                heading=p.heading,
                cog=getattr(p, 'cog', None),
                timestamp=p.timestamp,
            )
            for p in positions
        ],
    )


@router.get("/replay", response_model=ReplayResponse)
async def get_replay_data(
    hours: int = Query(6, ge=1, le=48, description="Hours of history to replay"),
    session: AsyncSession = Depends(get_session),
) -> ReplayResponse:
    """Get historical position data for replay.

    Returns position snapshots grouped by timestamp for replay visualization.

    Args:
        hours: Number of hours of history to return.
        session: Database session.

    Returns:
        Replay frames with vessel positions at each timestamp.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)

    # Get all positions in time range
    query = (
        select(VesselPosition)
        .where(VesselPosition.timestamp >= start_time)
        .order_by(VesselPosition.timestamp)
    )
    result = await session.execute(query)
    positions = result.scalars().all()

    # Get vessel info for names
    vessel_query = select(Vessel)
    vessel_result = await session.execute(vessel_query)
    vessels_db = {v.mmsi: v for v in vessel_result.scalars().all()}

    # Group positions by timestamp (rounded to nearest 30 seconds)
    frames_dict: dict[datetime, list[dict]] = {}
    for p in positions:
        # Round timestamp to 30 second intervals
        ts = p.timestamp.replace(second=(p.timestamp.second // 30) * 30, microsecond=0)
        if ts not in frames_dict:
            frames_dict[ts] = []

        vessel_info = vessels_db.get(p.mmsi)
        frames_dict[ts].append({
            "mmsi": p.mmsi,
            "name": vessel_info.name if vessel_info else None,
            "lat": p.lat,
            "lon": p.lon,
            "speed_knots": p.speed_knots,
            "heading": p.heading,
            "cog": getattr(p, 'cog', None),
            "is_large": vessel_info.is_large if vessel_info else False,
            "loa_m": vessel_info.loa_m if vessel_info else None,
            "draft_m": vessel_info.draft_m if vessel_info else None,
        })

    # Convert to sorted frames
    frames = [
        ReplayFrame(timestamp=ts, vessels=vessels)
        for ts, vessels in sorted(frames_dict.items())
    ]

    return ReplayResponse(
        start_time=start_time,
        end_time=end_time,
        frame_count=len(frames),
        frames=frames,
    )


@router.get("/replay/stats")
async def get_replay_stats(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get statistics about available replay data.

    Returns:
        Stats including earliest/latest positions and total count.
    """
    from sqlalchemy import func

    # Get count and time range
    count_query = select(func.count(VesselPosition.id))
    count_result = await session.execute(count_query)
    total_positions = count_result.scalar() or 0

    if total_positions == 0:
        return {
            "total_positions": 0,
            "earliest": None,
            "latest": None,
            "hours_available": 0,
        }

    min_query = select(func.min(VesselPosition.timestamp))
    max_query = select(func.max(VesselPosition.timestamp))

    min_result = await session.execute(min_query)
    max_result = await session.execute(max_query)

    earliest = min_result.scalar()
    latest = max_result.scalar()

    hours_available = (latest - earliest).total_seconds() / 3600 if earliest and latest else 0

    return {
        "total_positions": total_positions,
        "earliest": earliest.isoformat() if earliest else None,
        "latest": latest.isoformat() if latest else None,
        "hours_available": round(hours_available, 1),
    }


@router.get("/tides", response_model=TideResponse)
async def get_tides(
    hours: int = Query(48, ge=1, le=168, description="Hours of predictions"),
) -> TideResponse:
    """Get tidal predictions for Hoek van Holland.

    Args:
        hours: Number of hours of predictions to return.

    Returns:
        Tidal predictions and high tide windows.
    """
    tide_service = TideService()
    predictions, high_tides = await tide_service.fetch_predictions()

    return TideResponse(
        location="Hoek van Holland",
        reference="NAP",
        predictions=[
            TidePredictionResponse(
                timestamp=p["timestamp"],
                water_level_cm=p["water_level_cm"],
            )
            for p in predictions
        ],
        high_tides=[
            HighTideWindowResponse(
                timestamp=w["peak_time"],
                water_level_cm=w["peak_level_cm"],
                window_start=w["window_start"],
                window_end=w["window_end"],
            )
            for w in high_tides
        ],
    )


@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    active_only: bool = Query(True, description="Only show active alerts"),
    session: AsyncSession = Depends(get_session),
) -> AlertListResponse:
    """List alerts.

    Args:
        active_only: If True, only return active (unresolved) alerts.
        session: Database session.

    Returns:
        List of alerts.
    """
    query = select(Alert).order_by(Alert.created_at.desc())

    if active_only:
        query = query.where(Alert.resolved_at == None)  # noqa: E711

    result = await session.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        alerts=[
            AlertResponse(
                id=a.id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                vessels=a.vessel_list,
                target_window=a.target_window,
                created_at=a.created_at,
                resolved_at=a.resolved_at,
            )
            for a in alerts
        ]
    )
