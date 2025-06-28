import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const protectedRoutes = ['/dashboard', '/settings'];
const setupRoutes = ['/auth/signup/llm-setup', '/auth/signup/integrations', '/auth/complete-setup', '/auth/signin/validate'];
const publicRoutes = ['/sign-in', '/sign-up', '/', '/api'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const firebaseToken = request.cookies.get('firebase-token');
  
  // Check if it's a protected route
  const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));
  const isSetupRoute = setupRoutes.some(route => pathname.startsWith(route));
  const isPublicRoute = publicRoutes.some(route => pathname.startsWith(route));
  const isApiRoute = pathname.startsWith('/api');

  // Allow all API routes to pass through (they have their own auth)
  if (isApiRoute) {
    return NextResponse.next();
  }

  // If no auth token and trying to access protected or setup routes
  if (!firebaseToken && (isProtectedRoute || isSetupRoute)) {
    const signInUrl = new URL('/sign-in', request.url);
    signInUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(signInUrl);
  }

  // Redirect authenticated users away from sign-in/sign-up pages
  if (firebaseToken && (pathname === '/sign-in' || pathname === '/sign-up')) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};