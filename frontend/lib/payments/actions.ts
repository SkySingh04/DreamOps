'use server';

import { redirect } from 'next/navigation';

// Payment actions - stub implementations
// Stripe integration has been removed from this project

export const checkoutAction = async (formData: FormData) => {
  const priceId = formData.get('priceId') as string;
  throw new Error('Payment integration has been removed');
};

export const customerPortalAction = async () => {
  throw new Error('Payment integration has been removed');
};
