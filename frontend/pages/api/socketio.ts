import { NextApiRequest, NextApiResponse } from 'next';
import { Server as ServerIO } from 'socket.io';
import { Server as NetServer } from 'http';

export type NextApiResponseServerIO = NextApiResponse & {
  socket: {
    server: NetServer & {
      io: ServerIO;
    };
  };
};

const SocketHandler = (req: NextApiRequest, res: NextApiResponseServerIO) => {
  if (res.socket.server.io) {
    console.log('Socket.IO already running');
  } else {
    console.log('Socket.IO not running, starting...');
    
    const io = new ServerIO(res.socket.server, {
      path: '/api/socketio',
      addTrailingSlash: false,
    });
    
    res.socket.server.io = io;

    io.on('connection', (socket) => {
      console.log('Client connected:', socket.id);

      socket.on('join-team', (teamId: number) => {
        socket.join(`team-${teamId}`);
        console.log(`Socket ${socket.id} joined team ${teamId}`);
      });

      socket.on('leave-team', (teamId: number) => {
        socket.leave(`team-${teamId}`);
        console.log(`Socket ${socket.id} left team ${teamId}`);
      });

      socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
      });
    });
  }
  res.end();
};

export default SocketHandler;