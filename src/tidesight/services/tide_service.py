"""Tide service for fetching tidal predictions."""

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from tidesight.config import settings


def generate_tidal_predictions(hours: int = 48) -> list[dict[str, Any]]:
    """Generate tidal predictions based on semi-diurnal tide model.

    Hoek van Holland has semi-diurnal tides with ~12.4 hour period.

    Args:
        hours: Number of hours to generate predictions for.

    Returns:
        List of predictions with timestamp and water_level_cm.
    """
    now = datetime.now(timezone.utc)
    predictions = []

    # Semi-diurnal tide parameters for Hoek van Holland
    period_hours = 12.42
    amplitude = 90  # cm
    mean_level = 10  # cm above NAP

    for minutes in range(0, hours * 60, 10):
        timestamp = now + timedelta(minutes=minutes)
        phase = (2 * math.pi * minutes / 60) / period_hours
        water_level = mean_level + amplitude * math.sin(phase)

        predictions.append({
            "timestamp": timestamp,
            "water_level_cm": round(water_level, 1),
        })

    return predictions


def parse_rws_response(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse RWS WaterInfo API response into prediction list."""
    series = raw_data.get("series", [])
    if not series:
        return []

    data_points = series[0].get("data", [])
    predictions = []

    for point in data_points:
        if len(point) >= 2:
            timestamp_str = point[0]
            water_level = point[1]

            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            predictions.append({
                "timestamp": timestamp,
                "water_level_cm": water_level,
            })

    return predictions


def find_high_tides(
    predictions: list[dict[str, Any]],
    window_hours: float = 2.0,
) -> list[dict[str, Any]]:
    """Find high tide peaks in prediction data."""
    if len(predictions) < 3:
        return []

    high_tides = []

    for i in range(1, len(predictions) - 1):
        prev_level = predictions[i - 1]["water_level_cm"]
        curr_level = predictions[i]["water_level_cm"]
        next_level = predictions[i + 1]["water_level_cm"]

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
    """Service for fetching and processing tidal predictions."""

    def __init__(
        self,
        api_url: str | None = None,
        location_code: str | None = None,
        window_hours: float | None = None,
    ) -> None:
        self.api_url = api_url or settings.rws_api_url
        self.location_code = location_code or settings.rws_location_code
        self.window_hours = window_hours or settings.cluster_window_hours

    async def fetch_predictions(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch tidal predictions, falling back to synthetic data."""
        now = datetime.now(timezone.utc)
        start_date = now.strftime("%Y-%m-%dT%H:%M:%S.001Z")
        end_date = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.001Z")

        params = {
            "mapType": "astronomische-getij",
            "locationCode": self.location_code,
            "startDate": start_date,
            "endDate": end_date,
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

        # Fallback to synthetic data
        predictions = generate_tidal_predictions(hours=48)
        high_tides = find_high_tides(predictions, self.window_hours)
        return predictions, high_tides
