"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        ais_api_key: API key for aisstream.io WebSocket connection.
        ais_ws_url: WebSocket URL for AIS stream.
        ais_bounding_box: Lat/lon bounds for Hoek van Holland approach
            [[lat_min, lon_min], [lat_max, lon_max]].
        rws_api_url: Base URL for Rijkswaterstaat WaterInfo API.
        rws_location_code: Location code for tidal predictions.
        large_vessel_draft_m: Minimum draft in meters to classify as large vessel.
        large_vessel_loa_m: Minimum length overall in meters to classify as large vessel.
        cluster_window_hours: Time window in hours for cluster detection.
        tide_refresh_minutes: Interval in minutes for refreshing tidal data.
        database_url: SQLite database URL.
    """

    ais_api_key: str = ""
    ais_ws_url: str = "wss://stream.aisstream.io/v0/stream"
    ais_bounding_box: list[list[float]] = [[51.95, 3.8], [52.05, 4.2]]

    rws_api_url: str = "https://waterinfo.rws.nl/api/chart/get"
    rws_location_code: str = "Hoek van Holland(HOEKVHLD)"

    large_vessel_draft_m: float = 17.37
    large_vessel_loa_m: float = 250.0
    cluster_window_hours: float = 2.0
    tide_refresh_minutes: int = 60

    database_url: str = "sqlite+aiosqlite:///tidesight.db"

    model_config = {"env_prefix": "TIDESIGHT_"}


settings = Settings()
