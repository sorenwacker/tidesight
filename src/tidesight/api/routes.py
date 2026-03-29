"""FastAPI REST API routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
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
from tidesight.models import Alert, HighTideWindow, TidePrediction, Vessel
from tidesight.services.predictor import calculate_distance_to_entry

router = APIRouter(prefix="/api")


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
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
) -> VesselListResponse:
    """List all tracked vessels.

    Args:
        large_only: If True, only return large (tide-bound) vessels.
        limit: Maximum number of vessels to return.
        session: Database session.

    Returns:
        List of vessel data.
    """
    query = select(Vessel).order_by(Vessel.updated_at.desc()).limit(limit)

    if large_only:
        query = query.where(Vessel.is_large == True)  # noqa: E712

    result = await session.execute(query)
    vessels = result.scalars().all()

    vessel_responses = []
    for v in vessels:
        distance = calculate_distance_to_entry(v.lat, v.lon) if v.lat and v.lon else None
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
                distance_nm=distance,
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
        distance_nm=distance,
        updated_at=vessel.updated_at,
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
