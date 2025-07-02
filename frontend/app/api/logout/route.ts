import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export async function POST() {
  const cookieStore = await cookies();
  
  // Clear both session and firebase tokens
  cookieStore.delete('session');
  cookieStore.delete('firebase-token');
  
  return NextResponse.json({ success: true });
}