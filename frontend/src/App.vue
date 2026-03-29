<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import VesselMap from './components/VesselMap.vue'
import TideTimeline from './components/TideTimeline.vue'
import ArrivalsTable from './components/ArrivalsTable.vue'
import AlertsPanel from './components/AlertsPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import type { Vessel, TideData, Alert } from './types'

// Store vessels as a Map for efficient updates
const vesselMap = ref<Map<number, Vessel>>(new Map())
const tideData = ref<TideData | null>(null)
const alerts = ref<Alert[]>([])
const selectedVessel = ref<Vessel | null>(null)

const { connected, messages } = useWebSocket()

// Convert map to array for components
const vessels = computed(() => Array.from(vesselMap.value.values()))

const largeVessels = computed(() =>
  vessels.value.filter(v => v.is_large)
)

const vesselCount = computed(() => vessels.value.length)
const largeCount = computed(() => largeVessels.value.length)

async function fetchVessels() {
  try {
    const response = await fetch('/api/vessels?max_age_minutes=60&limit=500')
    const data = await response.json()

    // Merge with existing vessels instead of replacing
    for (const vessel of data.vessels) {
      vesselMap.value.set(vessel.mmsi, vessel)
    }
  } catch (error) {
    console.error('Failed to fetch vessels:', error)
  }
}

async function fetchTides() {
  try {
    const response = await fetch('/api/tides?hours=48')
    tideData.value = await response.json()
  } catch (error) {
    console.error('Failed to fetch tides:', error)
  }
}

async function fetchAlerts() {
  try {
    const response = await fetch('/api/alerts')
    const data = await response.json()
    alerts.value = data.alerts
  } catch (error) {
    console.error('Failed to fetch alerts:', error)
  }
}

function handleVesselSelect(vessel: Vessel) {
  selectedVessel.value = vessel
}

// Process WebSocket messages
watch(messages, (newMessages) => {
  const latest = newMessages[newMessages.length - 1]
  if (!latest) return

  switch (latest.type) {
    case 'vessel_update':
      {
        const update = latest.data as Partial<Vessel> & { mmsi: number }
        const existing = vesselMap.value.get(update.mmsi)
        if (existing) {
          vesselMap.value.set(update.mmsi, { ...existing, ...update })
        } else {
          // Add new vessel from WebSocket
          vesselMap.value.set(update.mmsi, update as Vessel)
        }
      }
      break

    case 'alert_created':
      alerts.value.unshift(latest.data as Alert)
      break

    case 'alert_resolved':
      {
        const alertId = (latest.data as { id: string }).id
        alerts.value = alerts.value.filter(a => a.id !== alertId)
      }
      break
  }
}, { deep: true })

onMounted(() => {
  fetchVessels()
  fetchTides()
  fetchAlerts()

  // Refresh data periodically
  setInterval(fetchVessels, 30000)
  setInterval(fetchTides, 3600000)
  setInterval(fetchAlerts, 60000)
})
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Tidesight</h1>
      <div class="header-stats">
        <span class="stat">{{ vesselCount }} vessels</span>
        <span class="stat large">{{ largeCount }} large</span>
      </div>
      <div class="connection-status">
        <span :class="['status-dot', connected ? 'connected' : 'disconnected']"></span>
        <span>{{ connected ? 'Live' : 'Offline' }}</span>
      </div>
    </header>

    <main class="main-content">
      <div class="map-container">
        <VesselMap :vessels="vessels" @select="handleVesselSelect" />
      </div>

      <div class="side-panel">
        <ArrivalsTable :vessels="largeVessels" />
        <AlertsPanel :alerts="alerts" />
      </div>

      <TideTimeline :tide-data="tideData" />
    </main>
  </div>
</template>

<style scoped>
.header-stats {
  display: flex;
  gap: 1rem;
}

.stat {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.stat.large {
  color: var(--danger-color);
  font-weight: 500;
}
</style>
