"""Predictor service for ETA calculation and tidal window matching."""

import math
from datetime import datetime, timedelta
from typing import Any

from tidesight.config import settings

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0

# Conversion factor
NM_TO_KM = 1.852

# Hoek van Holland entry point coordinates
HOEK_VAN_HOLLAND_LAT = 51.9792
HOEK_VAN_HOLLAND_LON = 4.1167


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in kilometers.

    Uses the haversine formula for calculating distance on a sphere.

    Args:
        lat1: Latitude of first point in decimal degrees.
        lon1: Longitude of first point in decimal degrees.
        lat2: Latitude of second point in decimal degrees.
        lon2: Longitude of second point in decimal degrees.

    Returns:
        Distance in kilometers.
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in nautical miles.

    Args:
        lat1: Latitude of first point in decimal degrees.
        lon1: Longitude of first point in decimal degrees.
        lat2: Latitude of second point in decimal degrees.
        lon2: Longitude of second point in decimal degrees.

    Returns:
        Distance in nautical miles.
    """
    return haversine_km(lat1, lon1, lat2, lon2) / NM_TO_KM


def is_large_vessel(
    draft_m: float | None = None,
    loa_m: float | None = None,
    draft_threshold: float | None = None,
    loa_threshold: float | None = None,
) -> bool:
    """Determine if vessel is large (tide-bound) based on dimensions.

    A vessel is considered large if its draft OR length overall exceeds
    the configured thresholds.

    Args:
        draft_m: Vessel draft in meters.
        loa_m: Vessel length overall in meters.
        draft_threshold: Override draft threshold (default from settings).
        loa_threshold: Override LOA threshold (default from settings).

    Returns:
        True if vessel meets large vessel criteria.
    """
    draft_threshold = draft_threshold or settings.large_vessel_draft_m
    loa_threshold = loa_threshold or settings.large_vessel_loa_m

    draft_exceeds = draft_m is not None and draft_m >= draft_threshold
    loa_exceeds = loa_m is not None and loa_m >= loa_threshold

    return draft_exceeds or loa_exceeds


def calculate_eta(
    lat: float,
    lon: float,
    speed_knots: float,
    target_lat: float = HOEK_VAN_HOLLAND_LAT,
    target_lon: float = HOEK_VAN_HOLLAND_LON,
    current_time: datetime | None = None,
) -> datetime | None:
    """Calculate estimated time of arrival at target point.

    Uses current position and speed to estimate arrival time.
    Returns None for stationary vessels.

    Args:
        lat: Current latitude in decimal degrees.
        lon: Current longitude in decimal degrees.
        speed_knots: Speed over ground in knots.
        target_lat: Target latitude (default: Hoek van Holland).
        target_lon: Target longitude (default: Hoek van Holland).
        current_time: Current timestamp (default: now).

    Returns:
        Estimated arrival datetime or None if vessel is stationary.
    """
    if speed_knots <= 0:
        return None

    if current_time is None:
        current_time = datetime.now(tz=datetime.now().astimezone().tzinfo)

    distance_nm = haversine_nm(lat, lon, target_lat, target_lon)
    travel_hours = distance_nm / speed_knots

    return current_time + timedelta(hours=travel_hours)


def find_target_window(
    eta: datetime,
    windows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the tidal window a vessel is targeting.

    If ETA falls within a window, returns that window.
    Otherwise returns the next upcoming window after ETA.

    Args:
        eta: Estimated time of arrival.
        windows: List of high tide windows with window_start, window_end, peak_time.

    Returns:
        Matching window dictionary or None if no windows available.
    """
    if not windows:
        return None

    # Sort windows by peak time
    sorted_windows = sorted(windows, key=lambda w: w["peak_time"])

    # Check if ETA falls within any window
    for window in sorted_windows:
        if window["window_start"] <= eta <= window["window_end"]:
            return window

    # Find next window after ETA
    for window in sorted_windows:
        if window["window_start"] > eta:
            return window

    # ETA before all windows - return first
    return sorted_windows[0]


def calculate_distance_to_entry(lat: float, lon: float) -> float:
    """Calculate distance to Hoek van Holland entry point in kilometers.

    Args:
        lat: Current latitude in decimal degrees.
        lon: Current longitude in decimal degrees.

    Returns:
        Distance in kilometers.
    """
    return haversine_km(lat, lon, HOEK_VAN_HOLLAND_LAT, HOEK_VAN_HOLLAND_LON)


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial bearing from point 1 to point 2.

    Args:
        lat1: Latitude of starting point.
        lon1: Longitude of starting point.
        lat2: Latitude of destination.
        lon2: Longitude of destination.

    Returns:
        Bearing in degrees (0-360, where 0=North, 90=East).
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
        lat2_rad
    ) * math.cos(delta_lon)

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def is_heading_towards_entry(
    lat: float,
    lon: float,
    cog: float | None,
    tolerance_degrees: float = 90.0,
) -> bool:
    """Check if vessel is heading towards Hoek van Holland.

    Compares the vessel's course over ground to the bearing towards the entry point.
    Returns True if the vessel is heading within tolerance degrees of the target.

    Args:
        lat: Current latitude.
        lon: Current longitude.
        cog: Course over ground in degrees (0-360).
        tolerance_degrees: Maximum angle difference to consider "heading towards".

    Returns:
        True if vessel is heading towards the entry point.
    """
    if cog is None:
        return False

    bearing_to_entry = calculate_bearing(
        lat, lon, HOEK_VAN_HOLLAND_LAT, HOEK_VAN_HOLLAND_LON
    )

    # Calculate angular difference (accounting for wrap-around at 360)
    diff = abs(cog - bearing_to_entry)
    if diff > 180:
        diff = 360 - diff

    return diff <= tolerance_degrees
