import { ref, onMounted, onUnmounted } from 'vue'
import type { WebSocketMessage } from '../types'

export function useWebSocket() {
  const connected = ref(false)
  const messages = ref<WebSocketMessage[]>([])
  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null
  let reconnectDelay = 1000

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/live`

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
      reconnectDelay = 1000
      console.log('WebSocket connected')
    }

    ws.onclose = () => {
      connected.value = false
      console.log('WebSocket disconnected, reconnecting...')
      scheduleReconnect()
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage
        messages.value.push(message)

        // Keep only last 100 messages
        if (messages.value.length > 100) {
          messages.value.shift()
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
    }

    reconnectTimer = window.setTimeout(() => {
      connect()
      reconnectDelay = Math.min(reconnectDelay * 2, 30000)
    }, reconnectDelay)
  }

  function subscribe(mmsi: number) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'subscribe', mmsi }))
    }
  }

  function unsubscribe(mmsi: number) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'unsubscribe', mmsi }))
    }
  }

  function disconnect() {
    if (reconnectTimer !== null) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    messages,
    subscribe,
    unsubscribe,
  }
}
