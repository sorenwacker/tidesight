"""Tide prediction model for water level data."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tidesight.db.database import Base


class TidePrediction(Base):
    """SQLAlchemy model for tidal predictions.

    Stores water level predictions at 10-minute intervals from
    Rijkswaterstaat WaterInfo API.

    Attributes:
        id: Auto-incrementing primary key.
        location: Location name (e.g., "Hoek van Holland").
        timestamp: Prediction timestamp (UTC).
        water_level_cm: Predicted water level in cm above NAP.
        is_high_tide: Whether this is a local maximum (high tide peak).
        fetched_at: When this prediction was fetched from API.
    """

    __tablename__ = "tide_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    water_level_cm: Mapped[float] = mapped_column(Float, nullable=False)
    is_high_tide: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class HighTideWindow(Base):
    """SQLAlchemy model for high tide windows.

    Pre-calculated windows around high tide peaks when large vessels
    can safely enter the port.

    Attributes:
        id: Auto-incrementing primary key.
        location: Location name.
        peak_time: Time of high tide peak.
        peak_level_cm: Water level at peak in cm above NAP.
        window_start: Start of entry window.
        window_end: End of entry window.
    """

    __tablename__ = "high_tide_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    peak_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    peak_level_cm: Mapped[float] = mapped_column(Float, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
