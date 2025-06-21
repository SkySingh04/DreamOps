import { getUser, getUserWithTeam } from './queries';

export async function getCurrentUserTeamId(): Promise<number | null> {
  try {
    const user = await getUser();
    if (!user) return null;

    const userWithTeam = await getUserWithTeam(user.id);
    return userWithTeam?.teamId || null;
  } catch (error) {
    console.error('Error getting user team ID:', error);
    return null;
  }
}