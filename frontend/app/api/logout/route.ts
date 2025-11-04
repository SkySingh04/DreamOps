import { NextResponse } from 'next/server';

export async function POST() {
  // Auth is handled by authentik reverse proxy
  // No logout logic needed here
  return NextResponse.json({ success: true });
}