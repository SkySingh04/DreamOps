// Stripe integration removed - stub file to prevent import errors

export async function createCheckoutSession({ team, priceId }: any) {
  throw new Error('Stripe integration has been removed');
}

export async function createCustomerPortalSession(team: any) {
  throw new Error('Stripe integration has been removed');
}

export async function handleSubscriptionChange(subscription: any) {
  console.log('Stripe integration has been removed');
}

export async function getStripePrices() {
  return [];
}

export async function getStripeProducts() {
  return [];
}
