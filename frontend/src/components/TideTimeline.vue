<script setup lang="ts">
import { ref, watch } from 'vue'
import { Chart, registerables } from 'chart.js'
import type { TideData } from '../types'

Chart.register(...registerables)

const props = defineProps<{
  tideData: TideData | null
}>()

const chartCanvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function renderChart() {
  if (!chartCanvas.value || !props.tideData) return

  const ctx = chartCanvas.value.getContext('2d')
  if (!ctx) return

  if (chart) {
    chart.destroy()
  }

  const labels = props.tideData.predictions.map(p => formatTime(p.timestamp))
  const data = props.tideData.predictions.map(p => p.water_level_cm)

  // Create high tide window annotations
  const annotations: Record<string, object> = {}
  props.tideData.high_tides.forEach((ht, i) => {
    annotations[`window${i}`] = {
      type: 'box',
      xMin: labels.indexOf(formatTime(ht.window_start)),
      xMax: labels.indexOf(formatTime(ht.window_end)),
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      borderColor: 'rgba(16, 185, 129, 0.5)',
      borderWidth: 1,
    }
  })

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Water Level (cm NAP)',
          data,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          mode: 'index',
          intersect: false,
        },
      },
      scales: {
        x: {
          display: true,
          grid: {
            display: false,
          },
          ticks: {
            maxTicksLimit: 12,
          },
        },
        y: {
          display: true,
          title: {
            display: true,
            text: 'cm (NAP)',
          },
        },
      },
    },
  })
}

watch(() => props.tideData, (newData) => {
  if (newData && newData.predictions?.length) {
    renderChart()
  }
}, { immediate: true })
</script>

<template>
  <div class="card timeline-container">
    <div class="card-header">
      Tidal Predictions - {{ tideData?.location || 'Hoek van Holland' }}
    </div>
    <div class="card-body chart-container">
      <canvas v-show="tideData" ref="chartCanvas"></canvas>
      <div v-if="!tideData || !tideData.predictions?.length" class="empty-state">
        Loading tidal data...
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-container {
  height: 250px;
  position: relative;
}

.chart-container canvas {
  width: 100% !important;
  height: 100% !important;
}
</style>
