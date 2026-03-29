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
from tidesight.models import Alert, HighTideWindow, TidePrediction, Vessel, VesselPosition
from tidesight.services.predictor import calculate_distance_to_entry

router = APIRouter(prefix="/api")


class PositionPoint(BaseModel):
    """Single position in trajectory."""

    lat: float
    lon: float
    speed_knots: float
    heading: float | None
    timestamp: datetime


class TrajectoryResponse(BaseModel):
    """Vessel trajectory response."""

    mmsi: int
    name: str | None
    positions: list[PositionPoint]


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
    # Only show vessels updated within max_age_minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    query = select(Vessel).where(Vessel.updated_at >= cutoff).order_by(Vessel.updated_at.desc()).limit(limit)

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
                timestamp=p.timestamp,
            )
            for p in positions
        ],
    )


@router.get("/tides", response_model=TideResponse)
async def get_tides(
    hours: int = Query(48, ge=1, le=168, description="Hours of predictions"),
    session: AsyncSession = Depends(get_session),
) -> TideResponse:
    """Get tidal predictions for Hoek van Holland.

    Args:
        hours: Number of hours of predictions to return.
        session: Database session.

    Returns:
        Tidal predictions and high tide windows.
    """
    now = datetime.now(timezone.utc)
    end_time = now + timedelta(hours=hours)

    # Get predictions
    pred_query = (
        select(TidePrediction)
        .where(TidePrediction.timestamp >= now)
        .where(TidePrediction.timestamp <= end_time)
        .order_by(TidePrediction.timestamp)
    )
    pred_result = await session.execute(pred_query)
    predictions = pred_result.scalars().all()

    # Get high tide windows
    window_query = (
        select(HighTideWindow)
        .where(HighTideWindow.peak_time >= now)
        .order_by(HighTideWindow.peak_time)
    )
    window_result = await session.execute(window_query)
    windows = window_result.scalars().all()

    return TideResponse(
        location="Hoek van Holland",
        reference="NAP",
        predictions=[
            TidePredictionResponse(
                timestamp=p.timestamp,
                water_level_cm=p.water_level_cm,
            )
            for p in predictions
        ],
        high_tides=[
            HighTideWindowResponse(
                timestamp=w.peak_time,
                water_level_cm=w.peak_level_cm,
                window_start=w.window_start,
                window_end=w.window_end,
            )
            for w in windows
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
