<script setup lang="ts">
import { ref, computed } from 'vue'
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

const emit = defineEmits<{
  (e: 'frame', vessels: Vessel[]): void
  (e: 'stop'): void
}>()

const isLoading = ref(false)
const isPlaying = ref(false)
const replayData = ref<ReplayData | null>(null)
const currentFrameIndex = ref(0)
const hoursToLoad = ref(1)
const error = ref('')

let playInterval: number | null = null

const hasData = computed(() => replayData.value && replayData.value.frames.length > 0)

const currentTime = computed(() => {
  if (!hasData.value) return ''
  const frame = replayData.value!.frames[currentFrameIndex.value]
  return new Date(frame.timestamp).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
})

const progress = computed(() => {
  if (!hasData.value) return 0
  return currentFrameIndex.value
})

const maxFrames = computed(() => {
  return hasData.value ? replayData.value!.frames.length - 1 : 0
})

async function loadAndPlay() {
  error.value = ''
  isLoading.value = true
  stop()

  try {
    const res = await fetch(`/api/replay?hours=${hoursToLoad.value}`)
    if (!res.ok) throw new Error('Failed to load')

    const data = await res.json()
    replayData.value = data
    currentFrameIndex.value = 0

    if (data.frames.length > 0) {
      play()
    } else {
      error.value = 'No data available'
    }
  } catch (err) {
    error.value = 'Failed to load replay data'
    console.error(err)
  } finally {
    isLoading.value = false
  }
}

function play() {
  if (!hasData.value) return
  isPlaying.value = true
  emitCurrentFrame()

  playInterval = window.setInterval(() => {
    if (currentFrameIndex.value < replayData.value!.frames.length - 1) {
      currentFrameIndex.value++
      emitCurrentFrame()
    } else {
      // Auto return to live when replay ends
      stop()
    }
  }, 1000)
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
  replayData.value = null
  currentFrameIndex.value = 0
  emit('stop')
}

function emitCurrentFrame() {
  if (hasData.value) {
    emit('frame', replayData.value!.frames[currentFrameIndex.value].vessels as Vessel[])
  }
}

function seek(e: Event) {
  const target = e.target as HTMLInputElement
  currentFrameIndex.value = parseInt(target.value, 10)
  emitCurrentFrame()
}
</script>

<template>
  <div class="card">
    <div class="card-header">Replay</div>
    <div class="card-body">
      <div v-if="!hasData" class="load-controls">
        <select v-model="hoursToLoad" class="select">
          <option :value="1">1 hour</option>
          <option :value="3">3 hours</option>
          <option :value="6">6 hours</option>
        </select>
        <button @click="loadAndPlay" :disabled="isLoading" class="btn btn-primary">
          {{ isLoading ? 'Loading...' : 'Replay' }}
        </button>
      </div>

      <div v-else class="playback">
        <div class="time">{{ currentTime }}</div>
        <input
          type="range"
          :min="0"
          :max="maxFrames"
          :value="progress"
          @input="seek"
          class="slider"
        />
        <div class="controls">
          <button v-if="!isPlaying" @click="play" class="btn">Play</button>
          <button v-else @click="pause" class="btn">Pause</button>
          <button @click="stop" class="btn btn-live">Back to Live</button>
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </div>
</template>

<style scoped>
.card-body {
  padding: 0.75rem;
}

.load-controls {
  display: flex;
  gap: 0.5rem;
}

.select {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-color);
}

.btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-color);
  cursor: pointer;
}

.btn:hover {
  background: var(--bg-color);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.btn-live {
  background: var(--success-color);
  color: white;
  border-color: var(--success-color);
}

.playback {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.time {
  font-size: 1.25rem;
  font-weight: 600;
  text-align: center;
}

.slider {
  width: 100%;
}

.controls {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.error {
  color: var(--danger-color);
  font-size: 0.75rem;
  margin-top: 0.5rem;
}
</style>
