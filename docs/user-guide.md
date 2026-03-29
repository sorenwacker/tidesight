# User Guide

## Getting Started

### Prerequisites

1. **Python 3.12+** with UV package manager
2. **Node.js 18+** for frontend development
3. **aisstream.io API key** (free tier available)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/tidesight.git
cd tidesight

# Install Python dependencies
uv sync --all-extras

# Install frontend dependencies
cd frontend
npm install
```

### Configuration

Create a `.env` file in the project root:

```bash
TIDESIGHT_AIS_API_KEY=your_aisstream_api_key
```

Optional settings:

```bash
# Vessel classification thresholds
TIDESIGHT_LARGE_VESSEL_DRAFT_M=17.37
TIDESIGHT_LARGE_VESSEL_LOA_M=250.0

# Alert configuration
TIDESIGHT_CLUSTER_WINDOW_HOURS=2.0

# Data refresh intervals
TIDESIGHT_TIDE_REFRESH_MINUTES=60
```

### Running

Start the backend:

```bash
uv run uvicorn tidesight.main:app --reload
```

Start the frontend (separate terminal):

```bash
cd frontend
npm run dev
```

Access the dashboard at `http://localhost:5173`

## Dashboard Components

### Vessel Map

Interactive map displaying:

- **Blue markers**: Regular vessels
- **Red markers**: Large vessels (tide-bound)
- **Dashed lines**: Predicted vessel tracks

Click a vessel marker to see details including:

- Vessel name and MMSI
- Current speed and heading
- Draft and length
- Estimated time of arrival
- Target tidal window

### Tidal Timeline

Chart showing water level predictions for Hoek van Holland:

- **Blue line**: Water level (cm above NAP)
- **Green bands**: High tide windows when large vessels can enter
- **Vertical markers**: Predicted vessel arrivals

### Arrivals Table

Sortable table of approaching large vessels:

| Column | Description |
|--------|-------------|
| Name | Vessel name |
| MMSI | Maritime Mobile Service Identity |
| Draft | Current draft in meters |
| ETA | Estimated arrival time |
| Window | Target high tide window |
| Distance | Distance to Hoek van Holland |

### Alerts Panel

Notifications for significant events:

- **Cluster alerts**: Multiple large vessels targeting same tidal window
- Color coding by severity (info, warning, critical)

## Understanding Predictions

### ETA Calculation

Estimated time of arrival is calculated using:

1. **Current position** from AIS data
2. **Current speed** (speed over ground)
3. **Haversine distance** to Hoek van Holland entry point

Formula: `ETA = current_time + (distance / speed)`

### Tidal Windows

High tide windows are extracted from astronomical tide predictions:

1. Find local maxima in water level time series
2. Define window as +/- 2 hours around peak (configurable)
3. Match vessel ETAs to windows

### Cluster Detection

A cluster alert is generated when:

1. Two or more large vessels have ETAs within the same tidal window
2. Both vessels are actively approaching (speed > 0.5 knots)

## Troubleshooting

### No vessels appearing

- Verify AIS API key is set correctly
- Check backend logs for WebSocket connection errors
- Confirm bounding box includes target area

### Stale data

- Tidal data refreshes hourly by default
- AIS positions update in real-time
- Check backend health endpoint: `GET /api/health`

### WebSocket disconnects

The frontend automatically reconnects with exponential backoff.
Check browser console for connection status.
