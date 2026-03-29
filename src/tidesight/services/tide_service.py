"""Tide service for fetching tidal predictions."""

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from tidesight.config import settings


def parse_rws_response(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse RWS WaterInfo API response into prediction list.

    Args:
        raw_data: Raw JSON response from RWS API.

    Returns:
        List of predictions with timestamp and water_level_cm.
    """
    series = raw_data.get("series", [])
    if not series:
        return []

    data_points = series[0].get("data", [])
    predictions = []

    for point in data_points:
        if len(point) >= 2:
            timestamp_str = point[0]
            water_level = point[1]

            timestamp = datetime.fromisoformat(timestamp_str)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            predictions.append({
                "timestamp": timestamp,
                "water_level_cm": water_level,
            })

    return predictions


def generate_tidal_predictions(hours: int = 48) -> list[dict[str, Any]]:
    """Generate synthetic tidal predictions based on semi-diurnal tide model.

    Hoek van Holland has semi-diurnal tides with ~12.4 hour period.
    Mean high water springs: ~200cm NAP
    Mean low water springs: ~-150cm NAP

    Args:
        hours: Number of hours to generate predictions for.

    Returns:
        List of predictions with timestamp and water_level_cm.
    """
    now = datetime.now(timezone.utc)
    predictions = []

    # Semi-diurnal tide parameters for Hoek van Holland
    period_hours = 12.42  # Lunar semi-diurnal period
    amplitude = 175  # cm (half of tidal range)
    mean_level = 25  # cm above NAP

    for minutes in range(0, hours * 60, 10):  # 10-minute intervals
        timestamp = now + timedelta(minutes=minutes)
        # Simple sinusoidal model
        phase = (2 * math.pi * minutes / 60) / period_hours
        water_level = mean_level + amplitude * math.sin(phase)

        predictions.append({
            "timestamp": timestamp,
            "water_level_cm": round(water_level, 1),
        })

    return predictions


def find_high_tides(
    predictions: list[dict[str, Any]],
    window_hours: float = 2.0,
) -> list[dict[str, Any]]:
    """Find high tide peaks in prediction data.

    Detects local maxima in the water level time series and calculates
    entry windows around each peak.

    Args:
        predictions: List of predictions with timestamp and water_level_cm.
        window_hours: Hours before/after peak for entry window.

    Returns:
        List of high tide windows with peak_time, peak_level_cm,
        window_start, and window_end.
    """
    if len(predictions) < 3:
        return []

    high_tides = []

    for i in range(1, len(predictions) - 1):
        prev_level = predictions[i - 1]["water_level_cm"]
        curr_level = predictions[i]["water_level_cm"]
        next_level = predictions[i + 1]["water_level_cm"]

        # Check for local maximum
        if curr_level > prev_level and curr_level > next_level:
            peak_time = predictions[i]["timestamp"]
            window_delta = timedelta(hours=window_hours)

            high_tides.append({
                "peak_time": peak_time,
                "peak_level_cm": curr_level,
                "window_start": peak_time - window_delta,
                "window_end": peak_time + window_delta,
            })

    return high_tides


class TideService:
    """Service for fetching and processing tidal predictions.

    Attempts to fetch from Rijkswaterstaat WaterInfo API, falls back
    to synthetic data if unavailable.

    Attributes:
        api_url: Base URL for WaterInfo API.
        location_code: Location code for tidal data.
        window_hours: Hours for high tide window calculation.
    """

    def __init__(
        self,
        api_url: str | None = None,
        location_code: str | None = None,
        window_hours: float | None = None,
    ) -> None:
        """Initialize tide service with configuration.

        Args:
            api_url: Override API URL (default from settings).
            location_code: Override location code (default from settings).
            window_hours: Override window hours (default from settings).
        """
        self.api_url = api_url or settings.rws_api_url
        self.location_code = location_code or settings.rws_location_code
        self.window_hours = window_hours or settings.cluster_window_hours

    async def fetch_predictions(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch tidal predictions from RWS API or generate synthetic data.

        Returns:
            Tuple of (predictions, high_tides) where predictions is the
            raw time series and high_tides is the detected peak windows.
        """
        params = {
            "mapType": "astronomische-getij",
            "locationCode": self.location_code,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url,
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    raw_data = response.json()
                    predictions = parse_rws_response(raw_data)
                    if predictions:
                        high_tides = find_high_tides(predictions, self.window_hours)
                        return predictions, high_tides

        except httpx.HTTPError:
            pass

        # Fall back to synthetic data
        predictions = generate_tidal_predictions(hours=48)
        high_tides = find_high_tides(predictions, self.window_hours)
        return predictions, high_tides
