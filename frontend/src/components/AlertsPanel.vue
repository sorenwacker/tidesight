<script setup lang="ts">
import type { Alert } from '../types'

const props = defineProps<{
  alerts: Alert[]
}>()

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="card">
    <div class="card-header">Active Alerts</div>
    <div class="card-body">
      <div v-if="alerts.length > 0" class="alerts-list">
        <div
          v-for="alert in alerts"
          :key="alert.id"
          :class="['alert', `alert-${alert.severity}`]"
        >
          <div class="alert-header">
            <span class="alert-time">{{ formatTime(alert.created_at) }}</span>
            <span :class="['badge', `badge-${alert.severity}`]">
              {{ alert.severity.toUpperCase() }}
            </span>
          </div>
          <div class="alert-message">{{ alert.message }}</div>
          <div v-if="alert.vessels.length > 0" class="alert-vessels">
            Vessels: {{ alert.vessels.join(', ') }}
          </div>
        </div>
      </div>
      <div v-else class="empty-state">
        No active alerts
      </div>
    </div>
  </div>
</template>

<style scoped>
.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.25rem;
}

.alert-time {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.alert-message {
  font-weight: 500;
}

.alert-vessels {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

.badge-warning {
  background-color: var(--warning-color);
  color: white;
}

.badge-critical {
  background-color: var(--danger-color);
  color: white;
}
</style>
