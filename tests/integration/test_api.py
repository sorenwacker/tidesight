"""Integration tests for REST API."""

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tidesight.db.database import Base, get_session
from tidesight.main import app
from tidesight.models import Alert, Vessel


@pytest.fixture
async def test_session():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession):
    """Create a test client with overridden database session."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """Health endpoint returns OK status."""
        response = await client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestVesselsEndpoint:
    """Tests for vessels endpoints."""

    @pytest.mark.asyncio
    async def test_list_vessels_empty(self, client: AsyncClient) -> None:
        """Empty database returns empty list."""
        response = await client.get("/api/vessels")

        assert response.status_code == 200
        data = response.json()
        assert data["vessels"] == []

    @pytest.mark.asyncio
    async def test_list_vessels_with_data(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Returns vessels from database."""
        vessel = Vessel(
            mmsi=123456789,
            name="TEST VESSEL",
            lat=51.98,
            lon=4.05,
            speed_knots=12.5,
            is_large=False,
            updated_at=datetime.now(timezone.utc),
        )
        test_session.add(vessel)
        await test_session.commit()

        response = await client.get("/api/vessels")

        assert response.status_code == 200
        data = response.json()
        assert len(data["vessels"]) == 1
        assert data["vessels"][0]["mmsi"] == 123456789
        assert data["vessels"][0]["name"] == "TEST VESSEL"

    @pytest.mark.asyncio
    async def test_list_large_vessels_only(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Filter to large vessels only."""
        vessels = [
            Vessel(
                mmsi=111111111,
                lat=51.98,
                lon=4.05,
                is_large=True,
                updated_at=datetime.now(timezone.utc),
            ),
            Vessel(
                mmsi=222222222,
                lat=51.95,
                lon=4.00,
                is_large=False,
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        test_session.add_all(vessels)
        await test_session.commit()

        response = await client.get("/api/vessels?large_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["vessels"]) == 1
        assert data["vessels"][0]["mmsi"] == 111111111

    @pytest.mark.asyncio
    async def test_get_vessel_found(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Get specific vessel by MMSI."""
        vessel = Vessel(
            mmsi=123456789,
            name="SPECIFIC VESSEL",
            lat=51.98,
            lon=4.05,
            updated_at=datetime.now(timezone.utc),
        )
        test_session.add(vessel)
        await test_session.commit()

        response = await client.get("/api/vessels/123456789")

        assert response.status_code == 200
        data = response.json()
        assert data["mmsi"] == 123456789
        assert data["name"] == "SPECIFIC VESSEL"

    @pytest.mark.asyncio
    async def test_get_vessel_not_found(self, client: AsyncClient) -> None:
        """Return 404 for non-existent vessel."""
        response = await client.get("/api/vessels/999999999")

        assert response.status_code == 404


class TestTidesEndpoint:
    """Tests for tides endpoint."""

    @pytest.mark.asyncio
    async def test_get_tides_empty(self, client: AsyncClient) -> None:
        """Empty database returns empty predictions."""
        response = await client.get("/api/tides")

        assert response.status_code == 200
        data = response.json()
        assert data["location"] == "Hoek van Holland"
        assert data["reference"] == "NAP"
        assert data["predictions"] == []
        assert data["high_tides"] == []


class TestAlertsEndpoint:
    """Tests for alerts endpoint."""

    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, client: AsyncClient) -> None:
        """Empty database returns empty list."""
        response = await client.get("/api/alerts")

        assert response.status_code == 200
        data = response.json()
        assert data["alerts"] == []

    @pytest.mark.asyncio
    async def test_list_active_alerts(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Returns only active alerts by default."""
        alerts = [
            Alert(
                id="alert-1",
                alert_type="cluster",
                severity="warning",
                message="Test alert 1",
                vessel_mmsis="111111111,222222222",
                created_at=datetime.now(timezone.utc),
                resolved_at=None,
            ),
            Alert(
                id="alert-2",
                alert_type="cluster",
                severity="warning",
                message="Test alert 2",
                vessel_mmsis="333333333,444444444",
                created_at=datetime.now(timezone.utc),
                resolved_at=datetime.now(timezone.utc),  # Resolved
            ),
        ]
        test_session.add_all(alerts)
        await test_session.commit()

        response = await client.get("/api/alerts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["id"] == "alert-1"

    @pytest.mark.asyncio
    async def test_list_all_alerts(
        self, client: AsyncClient, test_session: AsyncSession
    ) -> None:
        """Returns all alerts when active_only=false."""
        alerts = [
            Alert(
                id="alert-1",
                alert_type="cluster",
                severity="warning",
                message="Test alert 1",
                vessel_mmsis="111111111,222222222",
                created_at=datetime.now(timezone.utc),
                resolved_at=None,
            ),
            Alert(
                id="alert-2",
                alert_type="cluster",
                severity="warning",
                message="Test alert 2",
                vessel_mmsis="333333333,444444444",
                created_at=datetime.now(timezone.utc),
                resolved_at=datetime.now(timezone.utc),
            ),
        ]
        test_session.add_all(alerts)
        await test_session.commit()

        response = await client.get("/api/alerts?active_only=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) == 2
