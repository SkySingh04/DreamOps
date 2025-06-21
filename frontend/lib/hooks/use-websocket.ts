'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface DashboardUpdate {
  type: 'metrics' | 'incident' | 'ai_action';
  data: any;
  teamId: number;
}

interface UseWebSocketOptions {
  teamId?: number;
  onMetricsUpdate?: (metrics: any) => void;
  onIncidentUpdate?: (incident: any) => void;
  onAiActionUpdate?: (action: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  autoConnect?: boolean;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    teamId,
    onMetricsUpdate,
    onIncidentUpdate,
    onAiActionUpdate,
    onConnect,
    onDisconnect,
    onError,
    autoConnect = true,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const socketRef = useRef<Socket | null>(null);

  const connect = useCallback(() => {
    // TEMPORARILY DISABLED - WebSocket connection disabled to prevent spam
    return;
    
    if (socketRef.current?.connected || !teamId) return;

    try {
      const socketURL = process.env.NODE_ENV === 'production' 
        ? window.location.origin 
        : 'http://localhost:3000';

      socketRef.current = io(socketURL, {
        path: '/api/socketio',
        addTrailingSlash: false,
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 3,
        reconnectionDelay: 5000,
        reconnectionDelayMax: 10000,
        timeout: 20000,
      });

      socketRef.current.on('connect', () => {
        setIsConnected(true);
        onConnect?.();
        
        // Join team room
        if (teamId) {
          socketRef.current?.emit('join-team', teamId);
        }
      });

      socketRef.current.on('disconnect', () => {
        setIsConnected(false);
        onDisconnect?.();
      });

      socketRef.current.on('connect_error', (error: Error) => {
        onError?.(error);
        setIsConnected(false);
      });

      // Dashboard update handler
      socketRef.current.on('dashboard-update', (update: DashboardUpdate) => {
        console.log('Received dashboard update:', update);
        
        switch (update.type) {
          case 'metrics':
            onMetricsUpdate?.(update.data);
            break;
          case 'incident':
            onIncidentUpdate?.(update.data);
            break;
          case 'ai_action':
            onAiActionUpdate?.(update.data);
            break;
        }
      });

    } catch (error) {
      onError?.(error as Error);
    }
  }, [teamId, onConnect, onDisconnect, onError, onMetricsUpdate, onIncidentUpdate, onAiActionUpdate]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      if (teamId) {
        socketRef.current.emit('leave-team', teamId);
      }
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, [teamId]);

  const sendMessage = useCallback((event: string, data: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  useEffect(() => {
    // DISABLED - WebSocket connection disabled
    // if (autoConnect) {
    //   connect();
    // }

    // return () => {
    //   disconnect();
    // };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    connect,
    disconnect,
    sendMessage,
  };
}