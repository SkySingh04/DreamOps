import { getUser } from '@/lib/db/queries';

export async function GET() {
  try {
    // Auth is handled by authentik reverse proxy
    // User info should be extracted from authentik headers
    const user = await getUser();
    return Response.json(user);
  } catch (error) {
    console.error('Error in /api/user:', error);
    return Response.json(null);
  }
}
