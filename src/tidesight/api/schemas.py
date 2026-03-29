"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VesselResponse(BaseModel):
    """Vessel data response model."""

    mmsi: int = Field(..., description="Maritime Mobile Service Identity")
    name: Optional[str] = Field(None, description="Vessel name")
    lat: float = Field(..., description="Latitude in decimal degrees")
    lon: float = Field(..., description="Longitude in decimal degrees")
    speed_knots: float = Field(0.0, description="Speed over ground in knots")
    heading: Optional[float] = Field(None, description="Heading in degrees")
    draft_m: Optional[float] = Field(None, description="Current draft in meters")
    loa_m: Optional[float] = Field(None, description="Length overall in meters")
    beam_m: Optional[float] = Field(None, description="Beam in meters")
    is_large: bool = Field(False, description="Whether vessel is tide-bound")
    eta: Optional[datetime] = Field(None, description="Estimated time of arrival")
    target_window: Optional[datetime] = Field(None, description="Target tidal window")
    distance_nm: Optional[float] = Field(None, description="Distance to entry in nm")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class VesselListResponse(BaseModel):
    """Response for listing vessels."""

    vessels: list[VesselResponse]


class TidePredictionResponse(BaseModel):
    """Single tide prediction data point."""

    timestamp: datetime
    water_level_cm: float


class HighTideWindowResponse(BaseModel):
    """High tide window information."""

    timestamp: datetime = Field(..., description="Peak time")
    water_level_cm: float = Field(..., description="Water level at peak")
    window_start: datetime
    window_end: datetime


class TideResponse(BaseModel):
    """Tidal predictions response."""

    location: str = Field("Hoek van Holland")
    reference: str = Field("NAP")
    predictions: list[TidePredictionResponse]
    high_tides: list[HighTideWindowResponse]


class AlertResponse(BaseModel):
    """Alert data response model."""

    id: str
    type: str = Field(..., alias="alert_type")
    severity: str
    message: str
    vessels: list[int]
    window: Optional[datetime] = Field(None, alias="target_window")
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class AlertListResponse(BaseModel):
    """Response for listing alerts."""

    alerts: list[AlertResponse]


class ErrorResponse(BaseModel):
    """Error response model."""

    code: str
    message: str


class ErrorWrapper(BaseModel):
    """Wrapped error response."""

    error: ErrorResponse


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
