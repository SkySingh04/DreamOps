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
  teamId: number;
}

export function initializeWebSocket(server: NetServer): SocketIOServer {
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

      // Join team room for team-specific updates
      socket.on('join-team', (teamId: number) => {
        socket.join(`team-${teamId}`);
        console.log(`Client ${socket.id} joined team ${teamId}`);
      });

      // Leave team room
      socket.on('leave-team', (teamId: number) => {
        socket.leave(`team-${teamId}`);
        console.log(`Client ${socket.id} left team ${teamId}`);
      });

      socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
      });
    });

    server.io = io;
  }

  return server.io;
}

export function broadcastToTeam(io: SocketIOServer, teamId: number, update: DashboardUpdate) {
  io.to(`team-${teamId}`).emit('dashboard-update', update);
}

export function broadcastMetricsUpdate(io: SocketIOServer, teamId: number, metrics: any) {
  broadcastToTeam(io, teamId, {
    type: 'metrics',
    data: metrics,
    teamId
  });
}

export function broadcastIncidentUpdate(io: SocketIOServer, teamId: number, incident: any) {
  broadcastToTeam(io, teamId, {
    type: 'incident',
    data: incident,
    teamId
  });
}

export function broadcastAiActionUpdate(io: SocketIOServer, teamId: number, action: any) {
  broadcastToTeam(io, teamId, {
    type: 'ai_action',
    data: action,
    teamId
  });
}