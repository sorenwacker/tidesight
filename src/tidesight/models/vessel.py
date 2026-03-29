"""Vessel model for AIS-tracked ships."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from tidesight.config import settings
from tidesight.db.database import Base


class Vessel(Base):
    """SQLAlchemy model for tracked vessels.

    Stores current position, dimensions, and calculated ETA for vessels
    in the monitored area.

    Attributes:
        mmsi: Maritime Mobile Service Identity (primary key).
        name: Vessel name from AIS static data.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        speed_knots: Speed over ground in knots.
        heading: True heading in degrees (where bow points).
        cog: Course over ground in degrees (actual direction of travel).
        draft_m: Current draft in meters.
        loa_m: Length overall in meters.
        beam_m: Beam (width) in meters.
        eta: Calculated estimated time of arrival at Hoek van Holland.
        target_window: Matched high tide window timestamp.
        updated_at: Last AIS update timestamp.
    """

    __tablename__ = "vessels"

    mmsi: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    speed_knots: Mapped[float] = mapped_column(Float, default=0.0)
    heading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cog: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    draft_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    loa_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    beam_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    target_window: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_large: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def check_is_large(self) -> bool:
        """Determine if vessel is large (tide-bound) based on draft or LOA.

        A vessel is considered large if its draft exceeds the configured
        threshold OR its length overall exceeds the configured threshold.

        Returns:
            True if vessel meets large vessel criteria.
        """
        draft_exceeds = self.draft_m is not None and self.draft_m >= settings.large_vessel_draft_m
        loa_exceeds = self.loa_m is not None and self.loa_m >= settings.large_vessel_loa_m
        return draft_exceeds or loa_exceeds

    def update_large_status(self) -> None:
        """Update the is_large flag based on current dimensions."""
        self.is_large = self.check_is_large()
