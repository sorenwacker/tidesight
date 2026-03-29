# API Reference

## REST API

Base URL: `http://localhost:8000/api`

### Vessels

#### List Vessels

```http
GET /api/vessels
```

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `large_only` | boolean | Filter to large vessels only |
| `limit` | integer | Maximum results (default: 100) |

Response:

```json
{
  "vessels": [
    {
      "mmsi": 123456789,
      "name": "CONTAINER SHIP",
      "lat": 51.98,
      "lon": 4.05,
      "speed_knots": 12.5,
      "heading": 85,
      "draft_m": 14.2,
      "loa_m": 366,
      "is_large": true,
      "eta": "2026-03-29T14:30:00Z",
      "target_window": "2026-03-29T15:00:00Z",
      "updated_at": "2026-03-29T12:15:30Z"
    }
  ]
}
```

#### Get Vessel

```http
GET /api/vessels/{mmsi}
```

Response:

```json
{
  "mmsi": 123456789,
  "name": "CONTAINER SHIP",
  "lat": 51.98,
  "lon": 4.05,
  "speed_knots": 12.5,
  "heading": 85,
  "draft_m": 14.2,
  "loa_m": 366,
  "beam_m": 51,
  "is_large": true,
  "eta": "2026-03-29T14:30:00Z",
  "target_window": "2026-03-29T15:00:00Z",
  "distance_nm": 15.3,
  "updated_at": "2026-03-29T12:15:30Z"
}
```

### Tides

#### Get Tidal Predictions

```http
GET /api/tides
```

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `hours` | integer | Hours of predictions (default: 48) |

Response:

```json
{
  "location": "Hoek van Holland",
  "reference": "NAP",
  "predictions": [
    {
      "timestamp": "2026-03-29T12:00:00Z",
      "water_level_cm": 45
    },
    {
      "timestamp": "2026-03-29T12:10:00Z",
      "water_level_cm": 52
    }
  ],
  "high_tides": [
    {
      "timestamp": "2026-03-29T15:00:00Z",
      "water_level_cm": 120,
      "window_start": "2026-03-29T13:00:00Z",
      "window_end": "2026-03-29T17:00:00Z"
    }
  ]
}
```

### Alerts

#### List Alerts

```http
GET /api/alerts
```

Query parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `active_only` | boolean | Only show active alerts (default: true) |

Response:

```json
{
  "alerts": [
    {
      "id": "alert-001",
      "type": "cluster",
      "severity": "warning",
      "message": "3 large vessels targeting 15:00 tidal window",
      "vessels": [123456789, 987654321, 111222333],
      "window": "2026-03-29T15:00:00Z",
      "created_at": "2026-03-29T12:00:00Z",
      "resolved_at": null
    }
  ]
}
```

## WebSocket API

### Live Updates

```
ws://localhost:8000/ws/live
```

Connection establishes a bidirectional channel for real-time updates.

#### Server Messages

**Vessel Update**

```json
{
  "type": "vessel_update",
  "data": {
    "mmsi": 123456789,
    "lat": 51.98,
    "lon": 4.05,
    "speed_knots": 12.5,
    "heading": 85,
    "eta": "2026-03-29T14:30:00Z"
  }
}
```

**Alert Created**

```json
{
  "type": "alert_created",
  "data": {
    "id": "alert-001",
    "type": "cluster",
    "severity": "warning",
    "message": "3 large vessels targeting 15:00 tidal window",
    "vessels": [123456789, 987654321, 111222333]
  }
}
```

**Alert Resolved**

```json
{
  "type": "alert_resolved",
  "data": {
    "id": "alert-001"
  }
}
```

#### Client Messages

**Subscribe to vessel**

```json
{
  "action": "subscribe",
  "mmsi": 123456789
}
```

**Unsubscribe from vessel**

```json
{
  "action": "unsubscribe",
  "mmsi": 123456789
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Vessel with MMSI 123456789 not found"
  }
}
```

Common error codes:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request parameters |
| `INTERNAL_ERROR` | 500 | Server error |
