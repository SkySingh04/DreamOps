// WebSocket hook for real-time updates

import { useEffect, useRef, useState, useCallback } from 'react';
import io, { Socket } from 'socket.io-client';
import { WebSocketMessage } from '../types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  autoConnect?: boolean;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    onMessage,
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
    
    if (socketRef.current?.connected) return;

    try {
      socketRef.current = io(WS_URL, {
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
      });

      socketRef.current.on('disconnect', () => {
        setIsConnected(false);
        onDisconnect?.();
      });

      socketRef.current.on('message', (data: WebSocketMessage) => {
        setLastMessage(data);
        onMessage?.(data);
      });

      socketRef.current.on('error', (error: Error) => {
        onError?.(error);
      });

      // Subscribe to specific event types
      socketRef.current.on('incident_update', (data: any) => {
        const message: WebSocketMessage = {
          type: 'incident_update',
          data,
          timestamp: new Date().toISOString(),
        };
        setLastMessage(message);
        onMessage?.(message);
      });

      socketRef.current.on('integration_status', (data: any) => {
        const message: WebSocketMessage = {
          type: 'integration_status',
          data,
          timestamp: new Date().toISOString(),
        };
        setLastMessage(message);
        onMessage?.(message);
      });

      socketRef.current.on('ai_action', (data: any) => {
        const message: WebSocketMessage = {
          type: 'ai_action',
          data,
          timestamp: new Date().toISOString(),
        };
        setLastMessage(message);
        onMessage?.(message);
      });

      socketRef.current.on('metric_update', (data: any) => {
        const message: WebSocketMessage = {
          type: 'metric_update',
          data,
          timestamp: new Date().toISOString(),
        };
        setLastMessage(message);
        onMessage?.(message);
      });
    } catch (error) {
      onError?.(error as Error);
    }
  }, [onConnect, onDisconnect, onError, onMessage]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, []);

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