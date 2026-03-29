<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import VesselMap from './components/VesselMap.vue'
import TideTimeline from './components/TideTimeline.vue'
import ArrivalsTable from './components/ArrivalsTable.vue'
import AlertsPanel from './components/AlertsPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import type { Vessel, TideData, Alert } from './types'

const vessels = ref<Vessel[]>([])
const tideData = ref<TideData | null>(null)
const alerts = ref<Alert[]>([])
const selectedVessel = ref<Vessel | null>(null)

const { connected, messages } = useWebSocket()

const largeVessels = computed(() =>
  vessels.value.filter(v => v.is_large)
)

async function fetchVessels() {
  try {
    const response = await fetch('/api/vessels')
    const data = await response.json()
    vessels.value = data.vessels
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
        const update = latest.data as Partial<Vessel>
        const index = vessels.value.findIndex(v => v.mmsi === update.mmsi)
        if (index >= 0) {
          vessels.value[index] = { ...vessels.value[index], ...update }
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
      <div class="connection-status">
        <span :class="['status-dot', connected ? 'connected' : 'disconnected']"></span>
        <span>{{ connected ? 'Connected' : 'Disconnected' }}</span>
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
