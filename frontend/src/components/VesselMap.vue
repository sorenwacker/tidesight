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

// Hoek van Holland center
const CENTER: L.LatLngTuple = [51.98, 4.1]
const ZOOM = 10

function createMarkerIcon(isLarge: boolean, heading: number | null): L.DivIcon {
  const color = isLarge ? '#dc2626' : '#2563eb'
  const rotation = heading !== null ? heading : 0
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
      existing.setLatLng([vessel.lat, vessel.lon])
      existing.setIcon(createMarkerIcon(vessel.is_large, vessel.heading))
      existing.setPopupContent(formatVesselPopup(vessel))
    } else {
      const marker = L.marker([vessel.lat, vessel.lon], {
        icon: createMarkerIcon(vessel.is_large, vessel.heading),
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
