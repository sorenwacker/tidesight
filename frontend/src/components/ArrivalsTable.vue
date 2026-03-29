<script setup lang="ts">
import type { Vessel } from '../types'

const props = defineProps<{
  vessels: Vessel[]
}>()

function formatEta(eta: string | null): string {
  if (!eta) return '-'
  return new Date(eta).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDistance(distance: number | null): string {
  if (distance === null) return '-'
  return `${distance.toFixed(1)} nm`
}

function formatWindow(window: string | null): string {
  if (!window) return '-'
  return new Date(window).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="card">
    <div class="card-header">Approaching Large Vessels</div>
    <div class="card-body">
      <table v-if="vessels.length > 0" class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Draft</th>
            <th>ETA</th>
            <th>Window</th>
            <th>Distance</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="vessel in vessels" :key="vessel.mmsi">
            <td>
              <strong>{{ vessel.name || `MMSI: ${vessel.mmsi}` }}</strong>
            </td>
            <td>{{ vessel.draft_m?.toFixed(1) || '-' }}m</td>
            <td>{{ formatEta(vessel.eta) }}</td>
            <td>{{ formatWindow(vessel.target_window) }}</td>
            <td>{{ formatDistance(vessel.distance_nm) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">
        No large vessels approaching
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
</style>
