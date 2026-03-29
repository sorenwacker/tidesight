"""Alerter service for detecting vessel clusters."""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tidesight.models import Alert, Vessel
from tidesight.models.alert import AlertSeverity


@dataclass
class Cluster:
    """A cluster of vessels targeting the same tidal window.

    Attributes:
        window: Target tidal window timestamp.
        vessels: List of vessel MMSIs in the cluster.
    """

    window: datetime
    vessels: list[int]

    @property
    def size(self) -> int:
        """Number of vessels in cluster."""
        return len(self.vessels)


def detect_clusters(
    vessels: list[dict[str, Any]],
    min_cluster_size: int = 2,
) -> list[Cluster]:
    """Detect clusters of vessels targeting the same tidal window.

    Groups vessels by their target window and returns clusters
    with at least min_cluster_size vessels.

    Args:
        vessels: List of vessel dicts with 'mmsi' and 'target_window' keys.
        min_cluster_size: Minimum number of vessels to form a cluster.

    Returns:
        List of Cluster objects for windows with multiple vessels.
    """
    # Group vessels by target window
    window_groups: dict[datetime, list[int]] = defaultdict(list)

    for vessel in vessels:
        target_window = vessel.get("target_window")
        mmsi = vessel.get("mmsi")

        if target_window is not None and mmsi is not None:
            window_groups[target_window].append(mmsi)

    # Create clusters for windows with multiple vessels
    clusters = []
    for window, vessel_list in window_groups.items():
        if len(vessel_list) >= min_cluster_size:
            clusters.append(Cluster(window=window, vessels=vessel_list))

    # Sort by window time
    clusters.sort(key=lambda c: c.window)

    return clusters


def determine_severity(cluster: Cluster) -> AlertSeverity:
    """Determine alert severity based on cluster size.

    Args:
        cluster: Cluster to evaluate.

    Returns:
        AlertSeverity based on number of vessels.
    """
    if cluster.size >= 4:
        return AlertSeverity.CRITICAL
    return AlertSeverity.WARNING
