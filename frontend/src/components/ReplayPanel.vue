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

let timer: number | null = null

const inReplay = computed(() => replayData.value !== null)
const frameCount = computed(() => replayData.value?.frames.length || 0)
const currentTime = computed(() => {
  if (!replayData.value || frameCount.value === 0) return ''
  return new Date(replayData.value.frames[frameIndex.value].timestamp)
    .toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
})

async function startReplay() {
  isLoading.value = true
  try {
    const res = await fetch('/api/replay?hours=1')
    const data = await res.json()
    if (data.frames && data.frames.length > 0) {
      replayData.value = data
      frameIndex.value = 0
      showFrame()
      play()
    }
  } catch (e) {
    console.error('Replay failed:', e)
  }
  isLoading.value = false
}

function showFrame() {
  if (replayData.value && frameIndex.value < frameCount.value) {
    emit('frame', replayData.value.frames[frameIndex.value].vessels as Vessel[])
  }
}

function play() {
  isPlaying.value = true
  timer = window.setInterval(() => {
    if (frameIndex.value < frameCount.value - 1) {
      frameIndex.value++
      showFrame()
    } else {
      backToLive()
    }
  }, 800)
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
    <template v-if="!inReplay">
      <button @click="startReplay" :disabled="isLoading" class="btn-replay">
        {{ isLoading ? 'Loading...' : 'Replay Last Hour' }}
      </button>
    </template>
    <template v-else>
      <div class="replay-active">
        <span class="time">{{ currentTime }}</span>
        <input type="range" :min="0" :max="frameCount - 1" :value="frameIndex" @input="onSlide" />
        <div class="btns">
          <button v-if="isPlaying" @click="pause">Pause</button>
          <button v-else @click="play">Play</button>
          <button @click="backToLive" class="btn-live">Live</button>
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

.btn-replay {
  width: 100%;
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

.replay-active {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.time {
  text-align: center;
  font-weight: bold;
  font-size: 1.1rem;
}

input[type="range"] {
  width: 100%;
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
