<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import L from 'leaflet'
import type { Vessel } from '../types'

const props = defineProps<{
  vessels: Vessel[]
}>()

const emit = defineEmits<{
  (e: 'select', vessel: Vessel): void
}>()

const mapContainer = ref<HTMLDivElement | null>(null)
let map: L.Map | null = null
const markers = new Map<number, L.Marker>()
const animations = new Map<number, { startLat: number; startLon: number; endLat: number; endLon: number; startTime: number }>()

// Hoek van Holland center
const CENTER: L.LatLngTuple = [51.98, 4.1]
const ZOOM = 10
const ANIMATION_DURATION = 400 // ms - matches frame interval exactly for continuous motion
let animationRunning = false

function animateMarkers() {
  const now = performance.now()

  for (const [mmsi, anim] of animations) {
    const marker = markers.get(mmsi)
    if (!marker) continue

    const elapsed = now - anim.startTime
    // Linear interpolation for constant velocity (no pauses)
    const progress = Math.min(elapsed / ANIMATION_DURATION, 1)

    const lat = anim.startLat + (anim.endLat - anim.startLat) * progress
    const lon = anim.startLon + (anim.endLon - anim.startLon) * progress

    marker.setLatLng([lat, lon])

    if (progress >= 1) {
      animations.delete(mmsi)
    }
  }

  if (animations.size > 0) {
    requestAnimationFrame(animateMarkers)
  } else {
    animationRunning = false
  }
}

function startAnimation(mmsi: number, startLat: number, startLon: number, endLat: number, endLon: number) {
  // If animation already exists for this vessel, update from current marker position
  const existing = animations.get(mmsi)
  if (existing) {
    const marker = markers.get(mmsi)
    if (marker) {
      const pos = marker.getLatLng()
      startLat = pos.lat
      startLon = pos.lng
    }
  }

  animations.set(mmsi, {
    startLat,
    startLon,
    endLat,
    endLon,
    startTime: performance.now(),
  })

  if (!animationRunning) {
    animationRunning = true
    requestAnimationFrame(animateMarkers)
  }
}

function createMarkerIcon(isLarge: boolean, heading: number | null, cog: number | null, speed: number): L.DivIcon {
  const color = isLarge ? '#dc2626' : '#2563eb'
  // Use COG (actual direction of travel) when moving, heading when stationary
  const rotation = speed > 0.5 && cog !== null ? cog : (heading ?? 0)
  return L.divIcon({
    className: 'vessel-marker',
    html: `<svg width="24" height="24" viewBox="0 0 24 24" fill="${color}" style="transform: rotate(${rotation}deg)">
      <path d="M12 2L4 22l8-4 8 4L12 2z"/>
    </svg>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  })
}

function formatVesselPopup(vessel: Vessel): string {
  const name = vessel.name || `MMSI: ${vessel.mmsi}`
  const speed = vessel.speed_knots?.toFixed(1) || '0'
  const draft = vessel.draft_m?.toFixed(1) || '-'
  const loa = vessel.loa_m?.toFixed(0) || '-'
  const distance = vessel.distance_km?.toFixed(1) || '-'
  const eta = vessel.eta
    ? new Date(vessel.eta).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    : '-'
  const type = vessel.is_large ? '<span style="color:#dc2626">Large (tide-bound)</span>' : 'Regular'

  return `
    <div style="min-width: 200px">
      <strong style="font-size: 14px">${name}</strong><br>
      <small style="color: #666">MMSI: ${vessel.mmsi}</small>
      <hr style="margin: 8px 0; border: none; border-top: 1px solid #eee">
      <table style="font-size: 12px; width: 100%">
        <tr><td>Type:</td><td>${type}</td></tr>
        <tr><td>Speed:</td><td>${speed} kn</td></tr>
        <tr><td>Draft:</td><td>${draft} m</td></tr>
        <tr><td>Length:</td><td>${loa} m</td></tr>
        <tr><td>Distance:</td><td>${distance} km</td></tr>
        <tr><td>ETA:</td><td>${eta}</td></tr>
      </table>
    </div>
  `
}

function updateMarkers() {
  if (!map) return

  const currentMmsis = new Set(props.vessels.map(v => v.mmsi))

  // Remove markers for vessels no longer present
  for (const [mmsi, marker] of markers) {
    if (!currentMmsis.has(mmsi)) {
      marker.remove()
      markers.delete(mmsi)
    }
  }

  // Add or update markers
  for (const vessel of props.vessels) {
    const existing = markers.get(vessel.mmsi)

    if (existing) {
      const currentPos = existing.getLatLng()
      // Only animate if position changed significantly
      const latDiff = Math.abs(currentPos.lat - vessel.lat)
      const lonDiff = Math.abs(currentPos.lng - vessel.lon)
      if (latDiff > 0.0001 || lonDiff > 0.0001) {
        startAnimation(vessel.mmsi, currentPos.lat, currentPos.lng, vessel.lat, vessel.lon)
      }
      existing.setIcon(createMarkerIcon(vessel.is_large, vessel.heading, vessel.cog, vessel.speed_knots))
      existing.setPopupContent(formatVesselPopup(vessel))
    } else {
      const marker = L.marker([vessel.lat, vessel.lon], {
        icon: createMarkerIcon(vessel.is_large, vessel.heading, vessel.cog, vessel.speed_knots),
        title: vessel.name || `MMSI: ${vessel.mmsi}`,
      })

      marker.bindPopup(formatVesselPopup(vessel), {
        maxWidth: 300,
      })

      marker.on('click', () => emit('select', vessel))
      marker.addTo(map)
      markers.set(vessel.mmsi, marker)
    }
  }
}

// Expose method to locate a vessel on the map
function locateVessel(mmsi: number) {
  const marker = markers.get(mmsi)
  if (marker && map) {
    map.setView(marker.getLatLng(), 12, { animate: true })
    marker.openPopup()
  }
}

// Expose the method to parent
defineExpose({ locateVessel })

onMounted(() => {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value).setView(CENTER, ZOOM)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(map)

  // Draw Hoek van Holland entry point
  L.circle([51.9792, 4.1167], {
    color: '#10b981',
    fillColor: '#10b981',
    fillOpacity: 0.2,
    radius: 500,
  }).addTo(map).bindPopup('Hoek van Holland Entry Point')

  updateMarkers()
})

watch(() => props.vessels, updateMarkers, { deep: true })
</script>

<template>
  <div ref="mapContainer" class="map"></div>
</template>

<style scoped>
.map {
  width: 100%;
  height: 100%;
}

:deep(.vessel-marker) {
  background: transparent;
  border: none;
}

:deep(.vessel-marker svg) {
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
  transition: transform 0.3s ease;
}

:deep(.leaflet-popup-content-wrapper) {
  border-radius: 8px;
}

:deep(.leaflet-popup-content) {
  margin: 12px;
}
</style>
