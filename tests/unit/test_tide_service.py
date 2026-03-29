"""Unit tests for tide service."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import Response

from tidesight.services.tide_service import (
    TideService,
    find_high_tides,
    parse_rws_response,
)


class TestParseRwsResponse:
    """Tests for parsing RWS WaterInfo API responses."""

    def test_parse_valid_response(self) -> None:
        """Parse a valid RWS API response with water levels."""
        raw_data = {
            "series": [
                {
                    "data": [
                        ["2026-03-29T12:00:00", 45],
                        ["2026-03-29T12:10:00", 52],
                        ["2026-03-29T12:20:00", 58],
                    ]
                }
            ]
        }

        result = parse_rws_response(raw_data)

        assert len(result) == 3
        assert result[0]["timestamp"] == datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        assert result[0]["water_level_cm"] == 45
        assert result[2]["water_level_cm"] == 58

    def test_parse_empty_response(self) -> None:
        """Handle empty API response gracefully."""
        raw_data = {"series": []}

        result = parse_rws_response(raw_data)

        assert result == []

    def test_parse_missing_series(self) -> None:
        """Handle missing series key."""
        raw_data = {}

        result = parse_rws_response(raw_data)

        assert result == []


class TestFindHighTides:
    """Tests for detecting high tide peaks."""

    def test_find_single_high_tide(self) -> None:
        """Detect a single high tide peak in data."""
        base_time = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        predictions = [
            {"timestamp": base_time, "water_level_cm": 50},
            {"timestamp": base_time + timedelta(hours=1), "water_level_cm": 80},
            {"timestamp": base_time + timedelta(hours=2), "water_level_cm": 120},
            {"timestamp": base_time + timedelta(hours=3), "water_level_cm": 100},
            {"timestamp": base_time + timedelta(hours=4), "water_level_cm": 60},
        ]

        high_tides = find_high_tides(predictions)

        assert len(high_tides) == 1
        assert high_tides[0]["peak_time"] == base_time + timedelta(hours=2)
        assert high_tides[0]["peak_level_cm"] == 120

    def test_find_multiple_high_tides(self) -> None:
        """Detect multiple high tide peaks."""
        base_time = datetime(2026, 3, 29, 0, 0, tzinfo=timezone.utc)
        predictions = [
            {"timestamp": base_time, "water_level_cm": 50},
            {"timestamp": base_time + timedelta(hours=3), "water_level_cm": 120},
            {"timestamp": base_time + timedelta(hours=6), "water_level_cm": 40},
            {"timestamp": base_time + timedelta(hours=9), "water_level_cm": 50},
            {"timestamp": base_time + timedelta(hours=12), "water_level_cm": 110},
            {"timestamp": base_time + timedelta(hours=15), "water_level_cm": 45},
        ]

        high_tides = find_high_tides(predictions)

        assert len(high_tides) == 2
        assert high_tides[0]["peak_level_cm"] == 120
        assert high_tides[1]["peak_level_cm"] == 110

    def test_high_tide_window_calculation(self) -> None:
        """Verify window start/end around peak."""
        base_time = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        predictions = [
            {"timestamp": base_time, "water_level_cm": 50},
            {"timestamp": base_time + timedelta(hours=2), "water_level_cm": 120},
            {"timestamp": base_time + timedelta(hours=4), "water_level_cm": 50},
        ]

        high_tides = find_high_tides(predictions, window_hours=2.0)

        assert len(high_tides) == 1
        peak = high_tides[0]
        assert peak["window_start"] == base_time + timedelta(hours=2) - timedelta(hours=2)
        assert peak["window_end"] == base_time + timedelta(hours=2) + timedelta(hours=2)

    def test_empty_predictions(self) -> None:
        """Handle empty predictions list."""
        high_tides = find_high_tides([])

        assert high_tides == []

    def test_monotonic_data_no_peaks(self) -> None:
        """No peaks in strictly increasing data."""
        base_time = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        predictions = [
            {"timestamp": base_time + timedelta(hours=i), "water_level_cm": 50 + i * 10}
            for i in range(5)
        ]

        high_tides = find_high_tides(predictions)

        assert high_tides == []


class TestTideService:
    """Tests for TideService class."""

    @pytest.mark.asyncio
    async def test_fetch_predictions_success(self, respx_mock) -> None:
        """Fetch and parse tidal predictions from API."""
        mock_response = {
            "series": [
                {
                    "data": [
                        ["2026-03-29T12:00:00", 45],
                        ["2026-03-29T13:00:00", 90],
                        ["2026-03-29T14:00:00", 120],
                        ["2026-03-29T15:00:00", 90],
                        ["2026-03-29T16:00:00", 45],
                    ]
                }
            ]
        }

        respx_mock.get("https://waterinfo.rws.nl/api/chart/get").mock(
            return_value=Response(200, json=mock_response)
        )

        service = TideService()
        predictions, high_tides = await service.fetch_predictions()

        assert len(predictions) == 5
        assert len(high_tides) == 1
        assert high_tides[0]["peak_level_cm"] == 120

    @pytest.mark.asyncio
    async def test_fetch_predictions_api_error(self, respx_mock) -> None:
        """Handle API error gracefully."""
        respx_mock.get("https://waterinfo.rws.nl/api/chart/get").mock(
            return_value=Response(500)
        )

        service = TideService()
        predictions, high_tides = await service.fetch_predictions()

        assert predictions == []
        assert high_tides == []


@pytest.fixture
def respx_mock():
    """Mock httpx requests."""
    import respx

    with respx.mock:
        yield respx
