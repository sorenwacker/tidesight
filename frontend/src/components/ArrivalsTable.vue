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
            <th>Draft</th>
            <th>Dist</th>
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
            <td>{{ vessel.draft_m?.toFixed(1) || '-' }}m</td>
            <td>{{ formatDistance(vessel.distance_km) }}km</td>
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
