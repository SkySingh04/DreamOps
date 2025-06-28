// Re-export all functions from API-based auth
// This maintains compatibility while moving away from direct DB access
export { 
  getUser, 
  getUserById,
  getActivityLogs
} from '@/lib/api/auth';