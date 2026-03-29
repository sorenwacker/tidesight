# Tidesight

Real-time dashboard for predicting large vessel arrivals at the Port of Rotterdam based on AIS tracking and tidal windows.

## Overview

Large vessels (draft >= 17.37m or LOA >= 250m) are tide-bound at Hoek van Holland. Tidesight combines AIS vessel positions with tidal predictions to forecast arrival times and detect cluster events when multiple large vessels target the same tidal window.

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

## Data Sources

- **AIS**: aisstream.io WebSocket API
- **Tides**: Rijkswaterstaat WaterInfo API (Hoek van Holland)

## License

MIT
