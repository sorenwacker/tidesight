"""Business logic services for Tidesight."""

from tidesight.services.ais_client import AISClient, AISMessage, AISMessageType
from tidesight.services.alerter import Cluster, detect_clusters, determine_severity
from tidesight.services.predictor import (
    calculate_distance_to_entry,
    calculate_eta,
    find_target_window,
    haversine_nm,
    is_large_vessel,
)
from tidesight.services.tide_service import TideService, find_high_tides, parse_rws_response

__all__ = [
    "AISClient",
    "AISMessage",
    "AISMessageType",
    "Cluster",
    "TideService",
    "calculate_distance_to_entry",
    "calculate_eta",
    "detect_clusters",
    "determine_severity",
    "find_high_tides",
    "find_target_window",
    "haversine_nm",
    "is_large_vessel",
    "parse_rws_response",
]
