<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Vessel } from '../types'

interface ReplayFrame {
  timestamp: string
  vessels: Vessel[]
}

interface ReplayData {
  frames: ReplayFrame[]
}

const emit = defineEmits<{
  (e: 'frame', vessels: Vessel[]): void
  (e: 'stop'): void
}>()

const isLoading = ref(false)
const replayData = ref<ReplayData | null>(null)
const frameIndex = ref(0)
const isPlaying = ref(false)
const replayHours = ref(1)

const hourOptions = [
  { value: 1, label: '1 hour' },
  { value: 6, label: '6 hours' },
  { value: 12, label: '12 hours' },
  { value: 24, label: '24 hours' },
]

let timer: number | null = null
let abortController: AbortController | null = null

const inReplay = computed(() => replayData.value !== null)
const frameCount = computed(() => replayData.value?.frames.length || 0)
const currentDateTime = computed(() => {
  if (!replayData.value || frameCount.value === 0) return ''
  const d = new Date(replayData.value.frames[frameIndex.value].timestamp)
  const yy = String(d.getFullYear()).slice(2)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  return `${yy}${mm}${dd} ${time}`
})

const progressPercent = computed(() => {
  if (frameCount.value <= 1) return 0
  return (frameIndex.value / (frameCount.value - 1)) * 100
})

async function startReplay() {
  isLoading.value = true
  abortController = new AbortController()
  try {
    const res = await fetch(`/api/replay?hours=${replayHours.value}`, { signal: abortController.signal })
    const data = await res.json()
    isLoading.value = false
    abortController = null
    if (data.frames && data.frames.length > 0) {
      replayData.value = data
      frameIndex.value = 0
      showFrame()
      play()
    }
  } catch (e) {
    isLoading.value = false
    abortController = null
    if ((e as Error).name !== 'AbortError') {
      console.error('Replay failed:', e)
    }
  }
}

function cancelLoading() {
  if (abortController) {
    abortController.abort()
  }
  isLoading.value = false
}

function showFrame() {
  if (replayData.value && frameIndex.value < frameCount.value) {
    emit('frame', replayData.value.frames[frameIndex.value].vessels as Vessel[])
  }
}

function play() {
  if (timer) clearInterval(timer)
  isPlaying.value = true
  timer = window.setInterval(() => {
    if (frameIndex.value < frameCount.value - 1) {
      frameIndex.value++
      showFrame()
    } else {
      backToLive()
    }
  }, 400)
}

function pause() {
  isPlaying.value = false
  if (timer) clearInterval(timer)
  timer = null
}

function backToLive() {
  pause()
  replayData.value = null
  frameIndex.value = 0
  emit('stop')
}

function onSlide(e: Event) {
  frameIndex.value = parseInt((e.target as HTMLInputElement).value)
  showFrame()
}
</script>

<template>
  <div class="replay">
    <template v-if="!inReplay && !isLoading">
      <div class="replay-options">
        <select v-model="replayHours" class="hours-select">
          <option v-for="opt in hourOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <button @click="startReplay" class="btn-replay">
          Replay
        </button>
      </div>
    </template>
    <template v-else-if="isLoading">
      <div class="loading">
        <span>Loading replay data...</span>
        <button type="button" @click="cancelLoading" class="btn-cancel">Cancel</button>
      </div>
    </template>
    <template v-else>
      <div class="replay-active">
        <span class="datetime">{{ currentDateTime }}</span>
        <div class="progress-container">
          <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <input type="range" class="slider" :min="0" :max="frameCount - 1" :value="frameIndex" @input="onSlide" />
        <div class="btns">
          <button v-if="isPlaying" type="button" @click="pause">Pause</button>
          <button v-else type="button" @click="play">Play</button>
          <button type="button" @click="backToLive" class="btn-live">Live</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.replay {
  padding: 0.5rem;
  background: var(--card-bg);
  border-radius: 6px;
  margin-top: 0.5rem;
}

.replay-options {
  display: flex;
  gap: 0.5rem;
}

.hours-select {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.btn-replay {
  flex: 1;
  padding: 0.5rem;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-replay:disabled {
  opacity: 0.5;
}

.loading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.btn-cancel {
  padding: 0.25rem 0.5rem;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-color);
  cursor: pointer;
}

.replay-active {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.datetime {
  text-align: center;
  font-weight: bold;
  font-size: 1.1rem;
  font-variant-numeric: tabular-nums;
}

.progress-container {
  width: 100%;
  height: 12px;
  background: #ddd;
  border-radius: 6px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #22c55e;
  border-radius: 6px;
}

.slider {
  width: 100%;
  margin: 0;
  cursor: pointer;
}

.btns {
  display: flex;
  gap: 0.5rem;
}

.btns button {
  flex: 1;
  padding: 0.4rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.btn-live {
  background: var(--success-color) !important;
  color: white !important;
  border-color: var(--success-color) !important;
}
</style>
