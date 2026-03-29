"""Pytest fixtures for Tidesight tests."""

from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tidesight.db.database import Base


@pytest.fixture
def sample_vessel_data() -> dict:
    """Sample vessel data for testing."""
    return {
        "mmsi": 123456789,
        "name": "TEST VESSEL",
        "lat": 51.98,
        "lon": 4.05,
        "speed_knots": 12.5,
        "heading": 85.0,
        "draft_m": 14.2,
        "loa_m": 366.0,
        "beam_m": 51.0,
    }


@pytest.fixture
def large_vessel_data() -> dict:
    """Sample large vessel data (tide-bound) for testing."""
    return {
        "mmsi": 987654321,
        "name": "LARGE CONTAINER",
        "lat": 51.95,
        "lon": 3.90,
        "speed_knots": 10.0,
        "heading": 90.0,
        "draft_m": 18.5,
        "loa_m": 400.0,
        "beam_m": 59.0,
    }


@pytest.fixture
def sample_tide_data() -> list[dict]:
    """Sample tidal prediction data for testing."""
    base_time = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
    return [
        {"timestamp": base_time.isoformat(), "water_level_cm": 45},
        {"timestamp": base_time.replace(hour=13).isoformat(), "water_level_cm": 75},
        {"timestamp": base_time.replace(hour=14).isoformat(), "water_level_cm": 105},
        {"timestamp": base_time.replace(hour=15).isoformat(), "water_level_cm": 120},
        {"timestamp": base_time.replace(hour=16).isoformat(), "water_level_cm": 105},
        {"timestamp": base_time.replace(hour=17).isoformat(), "water_level_cm": 75},
        {"timestamp": base_time.replace(hour=18).isoformat(), "water_level_cm": 45},
    ]


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session

    await engine.dispose()
