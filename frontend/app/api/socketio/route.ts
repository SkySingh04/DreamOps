import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  // Socket.IO requires a custom server setup which is not compatible with the App Router
  // This endpoint is kept for compatibility but WebSocket functionality is temporarily disabled
  return NextResponse.json({ message: 'WebSocket temporarily disabled' });
}

export async function POST(request: NextRequest) {
  // Socket.IO requires a custom server setup which is not compatible with the App Router
  // This endpoint is kept for compatibility but WebSocket functionality is temporarily disabled
  return NextResponse.json({ message: 'WebSocket temporarily disabled' });
}