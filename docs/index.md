# Tidesight

Real-time dashboard for predicting large vessel arrivals at the Port of Rotterdam based on AIS tracking and tidal windows.

## Overview

Large vessels with draft >= 17.37m or length overall (LOA) >= 250m are tide-bound at Hoek van Holland. These vessels can only safely enter the port during high tide windows when water depth is sufficient.

Tidesight combines:

- **AIS vessel tracking** from aisstream.io to monitor approaching vessels
- **Tidal predictions** from Rijkswaterstaat WaterInfo API for Hoek van Holland

This enables:

- Real-time vessel position monitoring
- Estimated time of arrival (ETA) calculation
- Tidal window matching for large vessels
- Cluster detection when multiple large vessels target the same window

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Set AIS API key
export TIDESIGHT_AIS_API_KEY=your_key_here

# Run backend
uv run uvicorn tidesight.main:app --reload

# Run frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Data Sources

| Source | Purpose | Update Frequency |
|--------|---------|------------------|
| aisstream.io | Vessel positions, dimensions | Real-time (WebSocket) |
| RWS WaterInfo | Tidal predictions | Hourly refresh |

## Large Vessel Criteria

A vessel is classified as "large" (tide-bound) if either:

- Draft >= 17.37 meters
- LOA >= 250 meters

These thresholds are configurable via environment variables.
