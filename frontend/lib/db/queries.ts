// Re-export all functions from API-based auth
// This maintains compatibility while moving away from direct DB access
export { 
  getUser, 
  getTeamByStripeCustomerId,
  updateTeamSubscription,
  getUserWithTeam,
  getActivityLogs,
  getTeamForUser
} from '@/lib/api/auth';