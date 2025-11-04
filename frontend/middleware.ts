import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Auth removed - handled by Authentik reverse proxy
export async function middleware(request: NextRequest) {
  // All routes are now public - Authentik handles authentication
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};