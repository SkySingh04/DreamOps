'use server';

import { redirect } from 'next/navigation';
// Stripe integration removed
import { withTeam } from '@/lib/auth/middleware';

export const checkoutAction = withTeam(async (formData, team) => {
  const priceId = formData.get('priceId') as string;
  throw new Error('Stripe integration has been removed');
});

export const customerPortalAction = withTeam(async (_, team) => {
  throw new Error('Stripe integration has been removed');
});
