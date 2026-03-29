"""Unit tests for alerter service."""

from datetime import datetime, timezone

import pytest

from tidesight.models.alert import AlertSeverity
from tidesight.services.alerter import Cluster, detect_clusters, determine_severity


class TestDetectClusters:
    """Tests for cluster detection."""

    def test_no_vessels_no_clusters(self) -> None:
        """Empty vessel list produces no clusters."""
        clusters = detect_clusters([])
        assert clusters == []

    def test_single_vessel_no_cluster(self) -> None:
        """Single vessel does not form a cluster."""
        vessels = [
            {
                "mmsi": 123456789,
                "target_window": datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
            }
        ]
        clusters = detect_clusters(vessels)
        assert clusters == []

    def test_two_vessels_same_window(self) -> None:
        """Two vessels in same window form a cluster."""
        window = datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc)
        vessels = [
            {"mmsi": 111111111, "target_window": window},
            {"mmsi": 222222222, "target_window": window},
        ]

        clusters = detect_clusters(vessels)

        assert len(clusters) == 1
        assert clusters[0].window == window
        assert set(clusters[0].vessels) == {111111111, 222222222}

    def test_three_vessels_same_window(self) -> None:
        """Three vessels in same window form a cluster."""
        window = datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc)
        vessels = [
            {"mmsi": 111111111, "target_window": window},
            {"mmsi": 222222222, "target_window": window},
            {"mmsi": 333333333, "target_window": window},
        ]

        clusters = detect_clusters(vessels)

        assert len(clusters) == 1
        assert len(clusters[0].vessels) == 3

    def test_multiple_windows_multiple_clusters(self) -> None:
        """Vessels in different windows form separate clusters."""
        window1 = datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc)
        window2 = datetime(2026, 3, 29, 22, 0, tzinfo=timezone.utc)
        vessels = [
            {"mmsi": 111111111, "target_window": window1},
            {"mmsi": 222222222, "target_window": window1},
            {"mmsi": 333333333, "target_window": window2},
            {"mmsi": 444444444, "target_window": window2},
        ]

        clusters = detect_clusters(vessels)

        assert len(clusters) == 2

    def test_mixed_cluster_and_lone_vessels(self) -> None:
        """Some vessels cluster, others alone."""
        window1 = datetime(2026, 3, 29, 10, 0, tzinfo=timezone.utc)
        window2 = datetime(2026, 3, 29, 22, 0, tzinfo=timezone.utc)
        vessels = [
            {"mmsi": 111111111, "target_window": window1},
            {"mmsi": 222222222, "target_window": window1},
            {"mmsi": 333333333, "target_window": window2},  # Alone
        ]

        clusters = detect_clusters(vessels)

        assert len(clusters) == 1
        assert clusters[0].window == window1

    def test_none_window_excluded(self) -> None:
        """Vessels without target window are excluded."""
        window = datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc)
        vessels = [
            {"mmsi": 111111111, "target_window": window},
            {"mmsi": 222222222, "target_window": window},
            {"mmsi": 333333333, "target_window": None},
        ]

        clusters = detect_clusters(vessels)

        assert len(clusters) == 1
        assert len(clusters[0].vessels) == 2


class TestDetermineSeverity:
    """Tests for cluster severity determination."""

    def test_two_vessels_warning(self) -> None:
        """Two vessels is warning severity."""
        cluster = Cluster(
            window=datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
            vessels=[111111111, 222222222],
        )
        assert determine_severity(cluster) == AlertSeverity.WARNING

    def test_three_vessels_warning(self) -> None:
        """Three vessels is still warning."""
        cluster = Cluster(
            window=datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
            vessels=[111111111, 222222222, 333333333],
        )
        assert determine_severity(cluster) == AlertSeverity.WARNING

    def test_four_or_more_critical(self) -> None:
        """Four or more vessels is critical."""
        cluster = Cluster(
            window=datetime(2026, 3, 29, 15, 0, tzinfo=timezone.utc),
            vessels=[111111111, 222222222, 333333333, 444444444],
        )
        assert determine_severity(cluster) == AlertSeverity.CRITICAL
