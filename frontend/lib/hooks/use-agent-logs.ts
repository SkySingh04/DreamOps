'use client'

import { useEffect, useState, useRef, useCallback } from 'react'

export interface AgentLogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS' | 'ALERT'
  message: string
  incident_id?: string
  integration?: string
  action_type?: string
  metadata?: Record<string, any>
  progress?: number
  stage?: string
}

export interface AgentLogStreamState {
  logs: AgentLogEntry[]
  isConnected: boolean
  activeIncidents: Set<string>
  currentStage?: string
  currentProgress?: number
}

export function useAgentLogs(incidentId?: string) {
  const [state, setState] = useState<AgentLogStreamState>({
    logs: [],
    isConnected: false,
    activeIncidents: new Set(),
    currentStage: undefined,
    currentProgress: undefined,
  })

  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    // Build URL with optional incident filter
    const params = new URLSearchParams()
    if (incidentId) {
      params.append('incident_id', incidentId)
    }
    params.append('client_id', `web-${Date.now()}`)

    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/agent-logs/stream?${params}`

    console.log('Connecting to agent logs stream:', url)

    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log('Agent logs stream connected')
      setState(prev => ({ ...prev, isConnected: true }))
      
      // Clear reconnect timeout on successful connection
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Handle heartbeat
        if (data.type === 'heartbeat') {
          return
        }

        // Handle log entry
        if (data.data) {
          const logEntry = data.data as AgentLogEntry
          
          setState(prev => {
            const newActiveIncidents = new Set(prev.activeIncidents)
            
            // Track active incidents
            if (logEntry.incident_id) {
              if (logEntry.stage === 'complete') {
                newActiveIncidents.delete(logEntry.incident_id)
                
                // Emit event for analysis completion
                if (logEntry.metadata?.analysis) {
                  window.dispatchEvent(new CustomEvent('agent-log-update', {
                    detail: {
                      incident_id: logEntry.incident_id,
                      stage: logEntry.stage,
                      metadata: logEntry.metadata
                    }
                  }))
                }
              } else if (logEntry.stage === 'activation') {
                newActiveIncidents.add(logEntry.incident_id)
              }
            }

            return {
              logs: [...prev.logs, logEntry].slice(-500), // Keep last 500 logs
              isConnected: true,
              activeIncidents: newActiveIncidents,
              currentStage: logEntry.stage || prev.currentStage,
              currentProgress: logEntry.progress ?? prev.currentProgress,
            }
          })
        }
      } catch (error) {
        console.error('Error parsing agent log:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('Agent logs stream error:', error)
      setState(prev => ({ ...prev, isConnected: false }))
      eventSource.close()
      
      // Attempt to reconnect after 5 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Attempting to reconnect to agent logs stream...')
        connect()
      }, 5000)
    }
  }, [incidentId])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    setState(prev => ({ ...prev, isConnected: false }))
  }, [])

  const clearLogs = useCallback(() => {
    setState(prev => ({ ...prev, logs: [] }))
  }, [])

  // Auto-connect on mount and clean up on unmount
  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    ...state,
    clearLogs,
    reconnect: connect,
    disconnect,
  }
}