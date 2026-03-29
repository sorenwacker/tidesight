<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import type { Vessel } from '../types'

interface ReplayFrame {
  timestamp: string
  vessels: Vessel[]
}

interface ReplayData {
  start_time: string
  end_time: string
  frame_count: number
  frames: ReplayFrame[]
}

interface ReplayStats {
  total_positions: number
  earliest: string | null
  latest: string | null
  hours_available: number
}

const emit = defineEmits<{
  (e: 'frame', vessels: Vessel[]): void
  (e: 'stop'): void
}>()

const isLoading = ref(false)
const isPlaying = ref(false)
const replayData = ref<ReplayData | null>(null)
const stats = ref<ReplayStats | null>(null)
const currentFrameIndex = ref(0)
const playbackSpeed = ref(1)
const hoursToLoad = ref(6)

let playInterval: number | null = null

const currentFrame = computed(() => {
  if (!replayData.value || replayData.value.frames.length === 0) return null
  return replayData.value.frames[currentFrameIndex.value]
})

const progress = computed(() => {
  if (!replayData.value || replayData.value.frames.length === 0) return 0
  return (currentFrameIndex.value / (replayData.value.frames.length - 1)) * 100
})

const currentTime = computed(() => {
  if (!currentFrame.value) return '-'
  return new Date(currentFrame.value.timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
})

async function loadStats() {
  try {
    const res = await fetch('/api/replay/stats')
    stats.value = await res.json()
  } catch (err) {
    console.error('Failed to load replay stats:', err)
  }
}

async function loadReplay() {
  isLoading.value = true
  stop()
  try {
    const res = await fetch(`/api/replay?hours=${hoursToLoad.value}`)
    replayData.value = await res.json()
    currentFrameIndex.value = 0
    if (replayData.value && replayData.value.frames.length > 0) {
      emitCurrentFrame()
    }
  } catch (err) {
    console.error('Failed to load replay data:', err)
  } finally {
    isLoading.value = false
  }
}

function emitCurrentFrame() {
  if (currentFrame.value) {
    emit('frame', currentFrame.value.vessels as Vessel[])
  }
}

function play() {
  if (!replayData.value || replayData.value.frames.length === 0) return
  isPlaying.value = true

  playInterval = window.setInterval(() => {
    if (currentFrameIndex.value < replayData.value!.frames.length - 1) {
      currentFrameIndex.value++
      emitCurrentFrame()
    } else {
      stop()
    }
  }, 1000 / playbackSpeed.value)
}

function pause() {
  isPlaying.value = false
  if (playInterval) {
    clearInterval(playInterval)
    playInterval = null
  }
}

function stop() {
  pause()
  currentFrameIndex.value = 0
  emit('stop')
}

function seekTo(index: number) {
  currentFrameIndex.value = Math.max(0, Math.min(index, (replayData.value?.frames.length || 1) - 1))
  emitCurrentFrame()
}

function handleSlider(event: Event) {
  const target = event.target as HTMLInputElement
  seekTo(parseInt(target.value, 10))
}

onUnmounted(() => {
  if (playInterval) clearInterval(playInterval)
})

// Load stats on mount
loadStats()
</script>

<template>
  <div class="card replay-panel">
    <div class="card-header">Replay</div>
    <div class="card-body">
      <div v-if="stats" class="stats">
        <span v-if="stats.hours_available > 0">
          {{ stats.hours_available }}h of data available
        </span>
        <span v-else>No replay data yet</span>
      </div>

      <div class="controls">
        <select v-model="hoursToLoad" class="hours-select">
          <option :value="1">1 hour</option>
          <option :value="3">3 hours</option>
          <option :value="6">6 hours</option>
          <option :value="12">12 hours</option>
          <option :value="24">24 hours</option>
        </select>
        <button @click="loadReplay" :disabled="isLoading" class="btn">
          {{ isLoading ? 'Loading...' : 'Load' }}
        </button>
      </div>

      <div v-if="replayData && replayData.frames.length > 0" class="playback">
        <div class="playback-controls">
          <button v-if="!isPlaying" @click="play" class="btn btn-play">Play</button>
          <button v-else @click="pause" class="btn">Pause</button>
          <button @click="stop" class="btn">Stop</button>
          <select v-model="playbackSpeed" class="speed-select">
            <option :value="0.5">0.5x</option>
            <option :value="1">1x</option>
            <option :value="2">2x</option>
            <option :value="4">4x</option>
            <option :value="8">8x</option>
          </select>
        </div>

        <div class="timeline">
          <input
            type="range"
            :min="0"
            :max="replayData.frames.length - 1"
            :value="currentFrameIndex"
            @input="handleSlider"
            class="slider"
          />
          <div class="time-display">
            {{ currentTime }} ({{ currentFrameIndex + 1 }}/{{ replayData.frames.length }})
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.replay-panel {
  margin-top: 1rem;
}

.stats {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.controls {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.hours-select,
.speed-select {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-color);
  font-size: 0.75rem;
}

.btn {
  padding: 0.25rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
  font-size: 0.75rem;
}

.btn:hover {
  background: var(--bg-color);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-play {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.playback {
  border-top: 1px solid var(--border-color);
  padding-top: 0.75rem;
}

.playback-controls {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.slider {
  width: 100%;
  cursor: pointer;
}

.time-display {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-align: center;
}
</style>
