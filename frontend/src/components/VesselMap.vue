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
const ZOOM = 11

function createMarkerIcon(isLarge: boolean): L.DivIcon {
  const color = isLarge ? '#dc2626' : '#2563eb'
  return L.divIcon({
    className: 'vessel-marker',
    html: `<svg width="24" height="24" viewBox="0 0 24 24" fill="${color}">
      <path d="M12 2L4 22l8-4 8 4L12 2z"/>
    </svg>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  })
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
      existing.setIcon(createMarkerIcon(vessel.is_large))
      if (vessel.heading !== null) {
        const iconElement = existing.getElement()
        if (iconElement) {
          iconElement.style.transform += ` rotate(${vessel.heading}deg)`
        }
      }
    } else {
      const marker = L.marker([vessel.lat, vessel.lon], {
        icon: createMarkerIcon(vessel.is_large),
        title: vessel.name || `MMSI: ${vessel.mmsi}`,
      })

      marker.on('click', () => emit('select', vessel))
      marker.addTo(map)
      markers.set(vessel.mmsi, marker)
    }
  }
}

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
  }).addTo(map).bindPopup('Hoek van Holland Entry')

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
}
</style>
