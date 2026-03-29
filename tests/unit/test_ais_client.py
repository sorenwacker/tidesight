"""Unit tests for AIS client."""

import json
from datetime import datetime, timezone

import pytest

from tidesight.services.ais_client import (
    AISMessage,
    AISMessageType,
    parse_ais_message,
    parse_position_report,
    parse_ship_static_data,
)


class TestParsePositionReport:
    """Tests for parsing AIS position reports."""

    def test_parse_valid_position_report(self) -> None:
        """Parse a complete position report message."""
        raw_message = {
            "MessageType": "PositionReport",
            "MetaData": {
                "MMSI": 123456789,
                "time_utc": "2026-03-29T12:30:00Z",
            },
            "Message": {
                "PositionReport": {
                    "Latitude": 51.98,
                    "Longitude": 4.05,
                    "Sog": 12.5,
                    "TrueHeading": 85,
                    "Cog": 87.5,
                }
            },
        }

        result = parse_position_report(raw_message)

        assert result is not None
        assert result["mmsi"] == 123456789
        assert result["lat"] == 51.98
        assert result["lon"] == 4.05
        assert result["speed_knots"] == 12.5
        assert result["heading"] == 85

    def test_parse_position_report_missing_heading(self) -> None:
        """Handle position report with unavailable heading (511)."""
        raw_message = {
            "MessageType": "PositionReport",
            "MetaData": {"MMSI": 123456789},
            "Message": {
                "PositionReport": {
                    "Latitude": 51.98,
                    "Longitude": 4.05,
                    "Sog": 10.0,
                    "TrueHeading": 511,  # Not available
                    "Cog": 90.0,
                }
            },
        }

        result = parse_position_report(raw_message)

        assert result is not None
        assert result["heading"] is None

    def test_parse_position_report_invalid_coordinates(self) -> None:
        """Reject position report with invalid coordinates."""
        raw_message = {
            "MessageType": "PositionReport",
            "MetaData": {"MMSI": 123456789},
            "Message": {
                "PositionReport": {
                    "Latitude": 91.0,  # Invalid
                    "Longitude": 4.05,
                    "Sog": 10.0,
                }
            },
        }

        result = parse_position_report(raw_message)

        assert result is None


class TestParseShipStaticData:
    """Tests for parsing AIS ship static data."""

    def test_parse_valid_static_data(self) -> None:
        """Parse complete ship static data message."""
        raw_message = {
            "MessageType": "ShipStaticData",
            "MetaData": {"MMSI": 123456789},
            "Message": {
                "ShipStaticData": {
                    "Name": "CONTAINER SHIP",
                    "Dimension": {
                        "A": 200,
                        "B": 166,
                        "C": 25,
                        "D": 26,
                    },
                    "MaximumStaticDraught": 142,  # Decimeters
                }
            },
        }

        result = parse_ship_static_data(raw_message)

        assert result is not None
        assert result["mmsi"] == 123456789
        assert result["name"] == "CONTAINER SHIP"
        assert result["loa_m"] == 366.0  # A + B
        assert result["beam_m"] == 51.0  # C + D
        assert result["draft_m"] == 14.2  # Decimeters to meters

    def test_parse_static_data_missing_dimensions(self) -> None:
        """Handle static data with missing dimensions."""
        raw_message = {
            "MessageType": "ShipStaticData",
            "MetaData": {"MMSI": 123456789},
            "Message": {
                "ShipStaticData": {
                    "Name": "UNKNOWN",
                }
            },
        }

        result = parse_ship_static_data(raw_message)

        assert result is not None
        assert result["mmsi"] == 123456789
        assert result["loa_m"] is None
        assert result["beam_m"] is None
        assert result["draft_m"] is None


class TestParseAISMessage:
    """Tests for the main AIS message parser."""

    def test_parse_position_report_message(self) -> None:
        """Dispatch position report to correct parser."""
        raw_message = {
            "MessageType": "PositionReport",
            "MetaData": {"MMSI": 123456789},
            "Message": {
                "PositionReport": {
                    "Latitude": 51.98,
                    "Longitude": 4.05,
                    "Sog": 12.5,
                    "TrueHeading": 85,
                }
            },
        }

        result = parse_ais_message(raw_message)

        assert result is not None
        assert result.message_type == AISMessageType.POSITION_REPORT
        assert result.mmsi == 123456789
        assert result.data["lat"] == 51.98

    def test_parse_static_data_message(self) -> None:
        """Dispatch static data to correct parser."""
        raw_message = {
            "MessageType": "ShipStaticData",
            "MetaData": {"MMSI": 987654321},
            "Message": {
                "ShipStaticData": {
                    "Name": "TEST SHIP",
                    "Dimension": {"A": 100, "B": 50, "C": 10, "D": 10},
                }
            },
        }

        result = parse_ais_message(raw_message)

        assert result is not None
        assert result.message_type == AISMessageType.SHIP_STATIC_DATA
        assert result.mmsi == 987654321
        assert result.data["name"] == "TEST SHIP"

    def test_parse_unknown_message_type(self) -> None:
        """Handle unknown message types gracefully."""
        raw_message = {
            "MessageType": "UnknownType",
            "MetaData": {"MMSI": 123456789},
            "Message": {},
        }

        result = parse_ais_message(raw_message)

        assert result is None

    def test_parse_malformed_message(self) -> None:
        """Handle malformed messages without crashing."""
        raw_message = {"incomplete": "data"}

        result = parse_ais_message(raw_message)

        assert result is None
