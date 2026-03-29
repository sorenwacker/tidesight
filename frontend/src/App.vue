<script setup lang="ts">
import { ref, computed, onMounted, watch, shallowRef } from 'vue'
import VesselMap from './components/VesselMap.vue'
import TideTimeline from './components/TideTimeline.vue'
import ArrivalsTable from './components/ArrivalsTable.vue'
import AlertsPanel from './components/AlertsPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import type { Vessel, TideData, Alert } from './types'

// Use shallowRef for better performance with large arrays
const vesselMap = shallowRef<Map<number, Vessel>>(new Map())
const tideData = ref<TideData | null>(null)
const alerts = ref<Alert[]>([])
const mapRef = ref<InstanceType<typeof VesselMap> | null>(null)
const largeOnly = ref(true)  // Default: only show large vessels

const { connected, messages } = useWebSocket()

// Convert map to array for components, apply filter
const vessels = computed(() => {
  const all = Array.from(vesselMap.value.values())
  return largeOnly.value ? all.filter(v => v.is_large) : all
})

const largeVessels = computed(() =>
  vessels.value.filter(v => v.is_large).slice(0, 50)
)

const vesselCount = computed(() => vesselMap.value.size)
const largeCount = computed(() => largeVessels.value.length)

async function fetchVessels() {
  try {
    const response = await fetch('/api/vessels?max_age_minutes=30&limit=300')
    const data = await response.json()

    // Replace map to trigger reactivity
    const newMap = new Map(vesselMap.value)
    for (const vessel of data.vessels) {
      newMap.set(vessel.mmsi, vessel)
    }
    vesselMap.value = newMap
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

function handleLocate(vessel: Vessel) {
  mapRef.value?.locateVessel(vessel.mmsi)
}

// Throttle WebSocket updates
let updateQueue: Map<number, Partial<Vessel>> = new Map()
let updateTimer: number | null = null

function processUpdateQueue() {
  if (updateQueue.size === 0) return

  const newMap = new Map(vesselMap.value)
  for (const [mmsi, update] of updateQueue) {
    const existing = newMap.get(mmsi)
    if (existing) {
      newMap.set(mmsi, { ...existing, ...update })
    } else {
      newMap.set(mmsi, update as Vessel)
    }
  }
  vesselMap.value = newMap
  updateQueue.clear()
}

// Process WebSocket messages with throttling
watch(messages, (newMessages) => {
  const latest = newMessages[newMessages.length - 1]
  if (!latest) return

  switch (latest.type) {
    case 'vessel_update':
      {
        const update = latest.data as Partial<Vessel> & { mmsi: number }
        updateQueue.set(update.mmsi, update)

        // Batch updates every 2 seconds
        if (!updateTimer) {
          updateTimer = window.setTimeout(() => {
            processUpdateQueue()
            updateTimer = null
          }, 2000)
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
  setInterval(fetchVessels, 60000)  // Every 60s instead of 30s
  setInterval(fetchTides, 3600000)
  setInterval(fetchAlerts, 60000)
})
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>Tidesight</h1>
      <div class="header-controls">
        <label class="toggle">
          <input type="checkbox" v-model="largeOnly">
          <span>Large only</span>
        </label>
        <span class="stat">{{ vessels.length }} shown</span>
      </div>
      <div class="connection-status">
        <span :class="['status-dot', connected ? 'connected' : 'disconnected']"></span>
        <span>{{ connected ? 'Live' : 'Offline' }}</span>
      </div>
    </header>

    <main class="main-content">
      <div class="map-container">
        <VesselMap ref="mapRef" :vessels="vessels" />
      </div>

      <div class="side-panel">
        <ArrivalsTable :vessels="largeVessels" @locate="handleLocate" />
        <AlertsPanel :alerts="alerts" />
      </div>

      <TideTimeline :tide-data="tideData" />
    </main>
  </div>
</template>

<style scoped>
.header-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.toggle input {
  width: 16px;
  height: 16px;
}

.stat {
  font-size: 0.875rem;
  color: var(--text-muted);
}
</style>
