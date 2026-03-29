<script setup lang="ts">
import type { Vessel } from '../types'

const props = defineProps<{
  vessels: Vessel[]
}>()

const emit = defineEmits<{
  (e: 'locate', vessel: Vessel): void
}>()

function formatEta(eta: string | null): string {
  if (!eta) return '-'
  return new Date(eta).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatWindow(window: string | null, eta: string | null): string {
  if (!window) return formatEta(eta)
  const windowTime = new Date(window)
  const etaTime = eta ? new Date(eta) : null
  const time = windowTime.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
  // Show waiting indicator if vessel arrives before window
  if (etaTime && etaTime < windowTime) {
    return `${time} (wait)`
  }
  return time
}

function formatDistance(distance: number | null): string {
  if (distance === null) return '-'
  return `${distance.toFixed(1)}`
}

function handleClick(vessel: Vessel) {
  emit('locate', vessel)
}
</script>

<template>
  <div class="card">
    <div class="card-header">Large Vessels ({{ vessels.length }})</div>
    <div class="card-body">
      <table v-if="vessels.length > 0" class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Length</th>
            <th>Dist</th>
            <th>Entry</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vessel in vessels" :key="vessel.mmsi">
            <td>
              <a href="#" class="vessel-link" @click.prevent="handleClick(vessel)">
                {{ vessel.name || `${vessel.mmsi}` }}
              </a>
            </td>
            <td>{{ vessel.loa_m?.toFixed(0) || '-' }}m</td>
            <td>{{ formatDistance(vessel.distance_km) }}km</td>
            <td>{{ formatWindow(vessel.target_window, vessel.eta) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        No large vessels detected
      </div>
    </div>
  </div>
</template>

<style scoped>
.card-body {
  padding: 0;
  max-height: 300px;
  overflow-y: auto;
}

.table {
  margin: 0;
}

.vessel-link {
  color: var(--primary-color);
  text-decoration: none;
  font-weight: 500;
  cursor: pointer;
}

.vessel-link:hover {
  text-decoration: underline;
}
</style>
