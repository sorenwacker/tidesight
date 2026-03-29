"""Vessel position history for trajectory tracking."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from tidesight.db.database import Base


class VesselPosition(Base):
    """Historical position record for vessel trajectory.

    Stores timestamped positions to enable trajectory visualization
    and movement analysis.

    Attributes:
        id: Auto-incrementing primary key.
        mmsi: Vessel MMSI (foreign key to vessels).
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        speed_knots: Speed over ground at this position.
        heading: Heading in degrees at this position.
        timestamp: When this position was recorded.
    """

    __tablename__ = "vessel_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mmsi: Mapped[int] = mapped_column(Integer, ForeignKey("vessels.mmsi"), index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    speed_knots: Mapped[float] = mapped_column(Float, default=0.0)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
