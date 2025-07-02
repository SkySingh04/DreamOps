import { Server as SocketIOServer } from 'socket.io';
import { Server as NetServer } from 'http';
import { NextApiRequest, NextApiResponse } from 'next';

export type NextApiResponseServerIO = NextApiResponse & {
  socket: {
    server: NetServer & {
      io?: SocketIOServer;
    };
  };
};

export interface DashboardUpdate {
  type: 'metrics' | 'incident' | 'ai_action';
  data: any;
  userId: number;
}

export function initializeWebSocket(server: NetServer & { io?: SocketIOServer }): SocketIOServer {
  if (!server.io) {
    console.log('Initializing Socket.IO server...');
    
    const io = new SocketIOServer(server, {
      path: '/api/socketio',
      addTrailingSlash: false,
      cors: {
        origin: process.env.NODE_ENV === 'production' ? false : ['http://localhost:3000'],
        methods: ['GET', 'POST']
      }
    });

    io.on('connection', (socket) => {
      console.log('Client connected:', socket.id);

      // Join user room for user-specific updates
      socket.on('join-user', (userId: number) => {
        socket.join(`user-${userId}`);
        console.log(`Client ${socket.id} joined user ${userId}`);
      });

      // Leave user room
      socket.on('leave-user', (userId: number) => {
        socket.leave(`user-${userId}`);
        console.log(`Client ${socket.id} left user ${userId}`);
      });

      socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
      });
    });

    server.io = io;
  }

  return server.io;
}

export function broadcastToUser(io: SocketIOServer, userId: number, update: DashboardUpdate) {
  io.to(`user-${userId}`).emit('dashboard-update', update);
}

export function broadcastMetricsUpdate(io: SocketIOServer, userId: number, metrics: any) {
  broadcastToUser(io, userId, {
    type: 'metrics',
    data: metrics,
    userId
  });
}

export function broadcastIncidentUpdate(io: SocketIOServer, userId: number, incident: any) {
  broadcastToUser(io, userId, {
    type: 'incident',
    data: incident,
    userId
  });
}

export function broadcastAiActionUpdate(io: SocketIOServer, userId: number, action: any) {
  broadcastToUser(io, userId, {
    type: 'ai_action',
    data: action,
    userId
  });
}