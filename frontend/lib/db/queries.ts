// Auth removed - handled by authentik reverse proxy
// User info will be passed via headers from authentik
import type { ActivityLog } from './schema';

export async function getUser() {
  // Auth is handled by authentik reverse proxy
  // User info should be read from headers
  return null;
}

export async function getUserById(id: string) {
  // Auth is handled by authentik reverse proxy
  return null;
}

export async function getActivityLogs(): Promise<ActivityLog[]> {
  // Auth is handled by authentik reverse proxy
  return [];
}