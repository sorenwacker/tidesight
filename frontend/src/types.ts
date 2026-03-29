export interface Vessel {
  mmsi: number
  name: string | null
  lat: number
  lon: number
  speed_knots: number
  heading: number | null
  cog: number | null
  draft_m: number | null
  loa_m: number | null
  beam_m: number | null
  is_large: boolean
  eta: string | null
  target_window: string | null
  distance_km: number | null
  updated_at: string
}

export interface TidePrediction {
  timestamp: string
  water_level_cm: number
}

export interface HighTideWindow {
  timestamp: string
  water_level_cm: number
  window_start: string
  window_end: string
}

export interface TideData {
  location: string
  reference: string
  predictions: TidePrediction[]
  high_tides: HighTideWindow[]
}

export interface Alert {
  id: string
  type: string
  severity: string
  message: string
  vessels: number[]
  window: string | null
  created_at: string
  resolved_at: string | null
}

export interface WebSocketMessage {
  type: 'vessel_update' | 'alert_created' | 'alert_resolved'
  data: Record<string, unknown>
  timestamp: string
}
