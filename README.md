# Tidesight

Real-time dashboard for predicting large vessel arrivals at the Port of Rotterdam based on AIS tracking and tidal windows.

## Overview

Large vessels (draft >= 17.37m or LOA >= 250m) are tide-bound at Hoek van Holland. Tidesight combines AIS vessel positions with tidal predictions to forecast arrival times and detect cluster events when multiple large vessels target the same tidal window.

## Features

- Real-time vessel tracking via AIS stream
- Interactive map with vessel positions and trajectories
- Tidal predictions from Rijkswaterstaat
- ETA calculations based on vessel speed and distance
- Cluster alerts when multiple vessels target the same tidal window
- Historical replay with smooth vessel movement interpolation
- WebSocket-based live updates

## Requirements

- Python 3.12+
- UV package manager
- Node.js 18+ (for frontend)

## Installation

```bash
# Install Python dependencies
uv sync --all-extras

# Install frontend dependencies
cd frontend && npm install
```

## Development

```bash
# Run backend
uv run uvicorn tidesight.main:app --reload

# Run frontend
cd frontend && npm run dev

# Run tests
uv run pytest

# Build documentation
uv run mkdocs serve
```

## Configuration

Set the following environment variables:

```bash
AISSTREAM_API_KEY=your_api_key  # Required for AIS data
```

## Data Sources

- **AIS**: aisstream.io WebSocket API
- **Tides**: Rijkswaterstaat WaterInfo API (Hoek van Holland)

## Documentation

Full documentation available at `docs/` or run `uv run mkdocs serve` to view locally.

## License

MIT
