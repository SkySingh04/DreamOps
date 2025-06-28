'use client';

import { useActionState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Loader2, CreditCard } from 'lucide-react';
import { updateAccount } from '@/app/(login)/actions';
import { User } from '@/lib/db/schema';
import useSWR from 'swr';
import { Suspense } from 'react';
import { PaymentButton } from '@/components/payments/payment-button';
import { AlertUsageCard } from '@/components/dashboard/alert-usage-card';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

type ActionState = {
  name?: string;
  error?: string;
  success?: string;
};

type AccountFormProps = {
  state: ActionState;
  nameValue?: string;
  emailValue?: string;
};

function AccountForm({
  state,
  nameValue = '',
  emailValue = ''
}: AccountFormProps) {
  return (
    <>
      <div>
        <Label htmlFor="name" className="mb-2">
          Name
        </Label>
        <Input
          id="name"
          name="name"
          placeholder="Enter your name"
          defaultValue={state.name || nameValue}
          required
        />
      </div>
      <div>
        <Label htmlFor="email" className="mb-2">
          Email
        </Label>
        <Input
          id="email"
          name="email"
          type="email"
          placeholder="test@test.com"
          value={emailValue}
          disabled
        />
      </div>
      {state.error && (
        <div className="text-red-500 text-sm">{state.error}</div>
      )}
      {state.success && (
        <div className="text-green-500 text-sm">{state.success}</div>
      )}
      <Button
        type="submit"
        className="bg-orange-500 hover:bg-orange-600 text-white"
      >
        Update Account
      </Button>
    </>
  );
}

function GeneralContent() {
  const { data: user, error, isLoading } = useSWR<User>('/api/user', fetcher);
  const [state, formAction, isPending] = useActionState<ActionState, FormData>(
    updateAccount,
    {}
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="text-red-500">
        Failed to load user data. Please try again.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Account Settings Card */}
      <Card>
        <CardHeader>
          <CardTitle>Account Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <form action={formAction} className="space-y-4">
            {isPending ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Updating account...</span>
              </div>
            ) : (
              <AccountForm
                state={state}
                nameValue={user.name || ''}
                emailValue={user.email}
              />
            )}
          </form>
        </CardContent>
      </Card>

      {/* Alert Usage Card */}
      <AlertUsageCard userId={user.id.toString()} />

      {/* Subscription Card */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Subscription & Billing
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">Current Plan</h3>
              <div className="flex items-center justify-between p-4 bg-gray-100 rounded-lg">
                <div>
                  <p className="font-medium text-lg">
                    {user.planName || 'Free'} Plan
                  </p>
                  <p className="text-sm text-gray-600">
                    {user.accountTier === 'free' && '3 alerts per month'}
                    {user.accountTier === 'starter' && '50 alerts per month'}
                    {user.accountTier === 'professional' && 'Unlimited alerts'}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold">
                    {user.accountTier === 'free' && '₹0'}
                    {user.accountTier === 'starter' && '₹999'}
                    {user.accountTier === 'professional' && '₹4,999'}
                  </p>
                  <p className="text-sm text-gray-600">per month</p>
                </div>
              </div>
            </div>

            {user.accountTier === 'free' && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Upgrade Your Plan</h3>
                <PaymentButton 
                  userId={user.id.toString()}
                  currentPlan={user.accountTier || 'free'}
                />
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function General() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }
    >
      <GeneralContent />
    </Suspense>
  );
}