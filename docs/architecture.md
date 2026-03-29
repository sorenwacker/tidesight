# Architecture

## System Overview

```
+-------------------------------------------------------------+
|                      Vue 3 Dashboard                         |
|  +----------+  +----------+  +----------+  +--------------+  |
|  | Live Map |  |  Tidal   |  | Arrivals |  |    Alerts    |  |
|  |          |  | Timeline |  |  Table   |  |    Panel     |  |
|  +----------+  +----------+  +----------+  +--------------+  |
+-----------------------------+-------------------------------+
                              | REST + WebSocket
+-----------------------------v-------------------------------+
|                      FastAPI Backend                         |
|  +-------------+  +-------------+  +---------------------+   |
|  |  REST API   |  |  WS Server  |  |  Background Tasks   |   |
|  | /vessels    |  |  /ws/live   |  |  - AIS ingestion    |   |
|  | /tides      |  |             |  |  - Tide refresh     |   |
|  | /alerts     |  |             |  |  - Arrival calc     |   |
|  +-------------+  +-------------+  +---------------------+   |
+-----------------------------+-------------------------------+
                              |
+-----------------------------v-------------------------------+
|                      Domain Layer                            |
|  +-------------+  +-------------+  +---------------------+   |
|  |   Vessel    |  |    Tide     |  |      Predictor      |   |
|  |   Tracker   |  |   Service   |  |  - ETA calculation  |   |
|  |             |  |             |  |  - Window matching  |   |
|  |             |  |             |  |  - Cluster detect   |   |
|  +-------------+  +-------------+  +---------------------+   |
+-----------------------------+-------------------------------+
                              |
+-----------------------------v-------------------------------+
|                     Data Sources                             |
|  +---------------------+       +-------------------------+   |
|  |  aisstream.io WS    |       |  RWS WaterInfo API      |   |
|  |  - PositionReport   |       |  - Astronomische getij  |   |
|  |  - ShipStaticData   |       |  - Hoek van Holland     |   |
|  +---------------------+       +-------------------------+   |
+-------------------------------------------------------------+
```

## Components

### Frontend (Vue 3)

Single-page application built with Vue 3 and Vite:

- **VesselMap**: Interactive map showing vessel positions using Leaflet
- **TideTimeline**: Chart displaying tidal predictions with high tide windows
- **ArrivalsTable**: List of approaching large vessels with ETAs
- **AlertsPanel**: Notifications for cluster events

### Backend (FastAPI)

Python backend providing REST API and WebSocket endpoints:

#### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vessels` | GET | List tracked vessels |
| `/api/vessels/{mmsi}` | GET | Get vessel details |
| `/api/tides` | GET | Get tidal predictions |
| `/api/alerts` | GET | List active alerts |

#### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/live` | Real-time vessel position updates |

### Services

#### AIS Client (`services/ais_client.py`)

WebSocket consumer connecting to aisstream.io:

- Subscribes to bounding box around Hoek van Holland
- Parses PositionReport messages (lat, lon, speed, heading)
- Parses ShipStaticData messages (MMSI, name, dimensions)
- Handles reconnection on connection loss

#### Tide Service (`services/tide_service.py`)

HTTP client for Rijkswaterstaat WaterInfo API:

- Fetches astronomical tide predictions
- Parses water level time series (10-minute intervals)
- Identifies high tide windows

#### Predictor (`services/predictor.py`)

Core prediction logic:

- Calculates ETA using haversine distance and vessel speed
- Matches ETAs to tidal windows
- Determines which vessels are tide-bound

#### Alerter (`services/alerter.py`)

Cluster detection:

- Groups vessels by target tidal window
- Generates alerts when >= 2 large vessels in same window

### Database (SQLite)

Local SQLite database storing:

- **vessels**: Current vessel states (position, dimensions)
- **tides**: Cached tidal predictions
- **alerts**: Generated cluster alerts

## Data Flow

1. **AIS Ingestion**: Background task connects to aisstream.io, receives vessel updates
2. **Vessel Storage**: Updates stored in SQLite, broadcast via WebSocket
3. **Tide Refresh**: Periodic task fetches tidal data from RWS API
4. **Prediction**: On vessel update, calculate ETA and match to tidal window
5. **Alert Check**: When large vessel ETA changes, check for clusters
6. **Client Update**: Push changes to connected frontends via WebSocket

## Configuration

All configuration via environment variables with `TIDESIGHT_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `TIDESIGHT_AIS_API_KEY` | (required) | aisstream.io API key |
| `TIDESIGHT_LARGE_VESSEL_DRAFT_M` | 17.37 | Draft threshold (meters) |
| `TIDESIGHT_LARGE_VESSEL_LOA_M` | 250.0 | LOA threshold (meters) |
| `TIDESIGHT_CLUSTER_WINDOW_HOURS` | 2.0 | Cluster detection window |
| `TIDESIGHT_TIDE_REFRESH_MINUTES` | 60 | Tide data refresh interval |
