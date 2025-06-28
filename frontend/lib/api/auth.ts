import { desc, and, eq, isNull } from 'drizzle-orm';
import { getDb } from '@/lib/db/drizzle';
import { activityLogs, teamMembers, teams, users } from '@/lib/db/schema';
import { cookies } from 'next/headers';
import { verifyToken } from '@/lib/auth/session';

export async function getUser() {
  const sessionCookie = (await cookies()).get('session');
  if (!sessionCookie || !sessionCookie.value) {
    return null;
  }

  const sessionData = await verifyToken(sessionCookie.value);
  if (
    !sessionData ||
    !sessionData.user ||
    typeof sessionData.user.id !== 'number'
  ) {
    return null;
  }

  if (new Date(sessionData.expires) < new Date()) {
    return null;
  }

  const db = await getDb();
  const user = await db
    .select()
    .from(users)
    .where(and(eq(users.id, sessionData.user.id), isNull(users.deletedAt)))
    .limit(1);

  if (user.length === 0) {
    return null;
  }

  return user[0];
}

export async function getTeamByStripeCustomerId(customerId: string) {
  const db = await getDb();
  const result = await db
    .select()
    .from(teams)
    .where(eq(teams.stripeCustomerId, customerId))
    .limit(1);

  return result.length > 0 ? result[0] : null;
}

export async function updateTeamSubscription(
  teamId: number,
  subscriptionData: {
    stripeSubscriptionId: string | null;
    stripeProductId: string | null;
    planName: string | null;
    subscriptionStatus: string;
  }
) {
  const db = await getDb();
  await db
    .update(teams)
    .set({
      ...subscriptionData,
      updatedAt: new Date()
    })
    .where(eq(teams.id, teamId));
}

export async function getUserWithTeam(userId: number) {
  const db = await getDb();
  const result = await db
    .select({
      user: users,
      teamId: teamMembers.teamId
    })
    .from(users)
    .leftJoin(teamMembers, eq(users.id, teamMembers.userId))
    .where(eq(users.id, userId))
    .limit(1);

  return result[0];
}

export async function getActivityLogs() {
  const user = await getUser();
  if (!user) {
    throw new Error('User not authenticated');
  }

  const db = await getDb();
  return await db
    .select({
      id: activityLogs.id,
      action: activityLogs.action,
      timestamp: activityLogs.timestamp,
      ipAddress: activityLogs.ipAddress,
      userName: users.name
    })
    .from(activityLogs)
    .leftJoin(users, eq(activityLogs.userId, users.id))
    .where(eq(activityLogs.userId, user.id))
    .orderBy(desc(activityLogs.timestamp))
    .limit(10);
}

export async function getTeamForUser() {
  const user = await getUser();
  if (!user) {
    return null;
  }

  const db = await getDb();
  const result = await db
    .select({
      team: teams,
    })
    .from(teamMembers)
    .leftJoin(teams, eq(teamMembers.teamId, teams.id))
    .where(eq(teamMembers.userId, user.id))
    .limit(1);

  if (result.length === 0) {
    return null;
  }

  // Get team members separately
  const teamId = result[0].team?.id;
  if (!teamId) {
    return null;
  }

  const teamMembersData = await db
    .select({
      id: teamMembers.id,
      userId: teamMembers.userId,
      teamId: teamMembers.teamId,
      role: teamMembers.role,
      joinedAt: teamMembers.joinedAt,
      user: {
        id: users.id,
        name: users.name,
        email: users.email,
      },
    })
    .from(teamMembers)
    .leftJoin(users, eq(teamMembers.userId, users.id))
    .where(eq(teamMembers.teamId, teamId));

  const team = result[0].team;
  if (!team) {
    return null;
  }

  return {
    id: team.id,
    name: team.name,
    createdAt: team.createdAt,
    updatedAt: team.updatedAt,
    stripeCustomerId: team.stripeCustomerId,
    stripeSubscriptionId: team.stripeSubscriptionId,
    stripeProductId: team.stripeProductId,
    planName: team.planName,
    subscriptionStatus: team.subscriptionStatus,
    teamMembers: teamMembersData.map(tm => ({
      id: tm.id,
      userId: tm.userId,
      teamId: tm.teamId,
      role: tm.role,
      joinedAt: tm.joinedAt,
      user: tm.user ? {
        id: tm.user.id,
        name: tm.user.name || '',
        email: tm.user.email,
      } : {
        id: 0,
        name: '',
        email: '',
      },
    })),
  };
}