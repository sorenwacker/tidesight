"""Unit tests for predictor service."""

from datetime import datetime, timedelta, timezone

import pytest

from tidesight.services.predictor import (
    calculate_eta,
    find_target_window,
    haversine_nm,
    is_large_vessel,
)


class TestHaversine:
    """Tests for haversine distance calculation."""

    def test_same_point_zero_distance(self) -> None:
        """Same point should have zero distance."""
        distance = haversine_nm(51.98, 4.05, 51.98, 4.05)
        assert distance == 0.0

    def test_known_distance(self) -> None:
        """Calculate a known distance between two points."""
        # Hoek van Holland (51.9792, 4.1167) to center of Rotterdam (51.9225, 4.4792)
        # Approximately 15 nautical miles
        distance = haversine_nm(51.9792, 4.1167, 51.9225, 4.4792)
        assert 12 < distance < 18  # Allow some tolerance

    def test_symmetric(self) -> None:
        """Distance should be same in both directions."""
        d1 = haversine_nm(51.98, 4.05, 52.00, 4.10)
        d2 = haversine_nm(52.00, 4.10, 51.98, 4.05)
        assert abs(d1 - d2) < 0.001


class TestIsLargeVessel:
    """Tests for large vessel classification."""

    def test_large_by_draft(self) -> None:
        """Vessel is large if draft exceeds threshold."""
        assert is_large_vessel(draft_m=18.0, loa_m=200.0) is True

    def test_large_by_loa(self) -> None:
        """Vessel is large if LOA exceeds threshold."""
        assert is_large_vessel(draft_m=10.0, loa_m=300.0) is True

    def test_large_by_both(self) -> None:
        """Vessel is large if both exceed thresholds."""
        assert is_large_vessel(draft_m=20.0, loa_m=400.0) is True

    def test_not_large(self) -> None:
        """Vessel is not large if neither exceeds threshold."""
        assert is_large_vessel(draft_m=10.0, loa_m=150.0) is False

    def test_boundary_draft(self) -> None:
        """Test exact threshold for draft."""
        assert is_large_vessel(draft_m=17.37, loa_m=100.0) is True
        assert is_large_vessel(draft_m=17.36, loa_m=100.0) is False

    def test_boundary_loa(self) -> None:
        """Test exact threshold for LOA."""
        assert is_large_vessel(draft_m=10.0, loa_m=250.0) is True
        assert is_large_vessel(draft_m=10.0, loa_m=249.0) is False

    def test_none_values(self) -> None:
        """Handle None dimensions gracefully."""
        assert is_large_vessel(draft_m=None, loa_m=None) is False
        assert is_large_vessel(draft_m=18.0, loa_m=None) is True
        assert is_large_vessel(draft_m=None, loa_m=300.0) is True


class TestCalculateEta:
    """Tests for ETA calculation."""

    def test_calculate_eta_stationary(self) -> None:
        """Stationary vessel returns None ETA."""
        now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        eta = calculate_eta(
            lat=51.95,
            lon=3.90,
            speed_knots=0.0,
            target_lat=51.9792,
            target_lon=4.1167,
            current_time=now,
        )
        assert eta is None

    def test_calculate_eta_moving(self) -> None:
        """Moving vessel gets calculated ETA."""
        now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        eta = calculate_eta(
            lat=51.95,
            lon=3.90,
            speed_knots=10.0,
            target_lat=51.9792,
            target_lon=4.1167,
            current_time=now,
        )

        assert eta is not None
        assert eta > now
        # At 10 knots, roughly 10-15nm should take 1-1.5 hours
        assert timedelta(hours=0.5) < (eta - now) < timedelta(hours=3)

    def test_calculate_eta_fast_vessel(self) -> None:
        """Faster vessel arrives sooner."""
        now = datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc)
        slow_eta = calculate_eta(
            lat=51.95, lon=3.90, speed_knots=5.0,
            target_lat=51.98, target_lon=4.05, current_time=now,
        )
        fast_eta = calculate_eta(
            lat=51.95, lon=3.90, speed_knots=15.0,
            target_lat=51.98, target_lon=4.05, current_time=now,
        )

        assert slow_eta is not None
        assert fast_eta is not None
        assert fast_eta < slow_eta


class TestFindTargetWindow:
    """Tests for matching ETA to tidal window."""

    def test_find_window_exact_match(self) -> None:
        """ETA within window returns that window."""
        windows = [
            {
                "peak_time": datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
                "window_start": datetime(2026, 3, 29, 13, 0, tzinfo=timezone.utc),
                "window_end": datetime(2026, 3, 29, 17, 0, tzinfo=timezone.utc),
            }
        ]
        eta = datetime(2026, 3, 29, 14, 30, tzinfo=timezone.utc)

        result = find_target_window(eta, windows)

        assert result is not None
        assert result["peak_time"] == windows[0]["peak_time"]

    def test_find_window_before_all(self) -> None:
        """ETA before all windows returns first window."""
        windows = [
            {
                "peak_time": datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
                "window_start": datetime(2026, 3, 29, 13, 0, tzinfo=timezone.utc),
                "window_end": datetime(2026, 3, 29, 17, 0, tzinfo=timezone.utc),
            }
        ]
        eta = datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc)

        result = find_target_window(eta, windows)

        assert result is not None
        assert result["peak_time"] == windows[0]["peak_time"]

    def test_find_window_between(self) -> None:
        """ETA between windows returns next window."""
        windows = [
            {
                "peak_time": datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc),
                "window_start": datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc),
                "window_end": datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            },
            {
                "peak_time": datetime(2026, 3, 29, 22, 0, tzinfo=timezone.utc),
                "window_start": datetime(2026, 3, 29, 20, 0, tzinfo=timezone.utc),
                "window_end": datetime(2026, 3, 30, 0, 0, tzinfo=timezone.utc),
            },
        ]
        eta = datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc)

        result = find_target_window(eta, windows)

        assert result is not None
        assert result["peak_time"] == windows[1]["peak_time"]

    def test_find_window_empty_list(self) -> None:
        """Empty window list returns None."""
        eta = datetime(2026, 3, 29, 14, 0, tzinfo=timezone.utc)

        result = find_target_window(eta, [])

        assert result is None
