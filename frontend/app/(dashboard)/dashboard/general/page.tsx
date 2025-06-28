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
          placeholder="Enter your email"
          defaultValue={emailValue}
          required
        />
      </div>
    </>
  );
}

function AccountFormWithData({ state }: { state: ActionState }) {
  const { data: user } = useSWR<User>('/api/user', fetcher);
  return (
    <AccountForm
      state={state}
      nameValue={user?.name ?? ''}
      emailValue={user?.email ?? ''}
    />
  );
}

export default function GeneralPage() {
  const [state, formAction, isPending] = useActionState<ActionState, FormData>(
    updateAccount,
    {}
  );

  return (
    <section className="flex-1 p-4 lg:p-8">
      <h1 className="text-lg lg:text-2xl font-medium text-gray-900 mb-6">
        General Settings
      </h1>

      {/* Alert Usage Overview */}
      <AlertUsageCard className="mb-6" teamId="team_123" />

      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" action={formAction}>
            <Suspense fallback={<AccountForm state={state} />}>
              <AccountFormWithData state={state} />
            </Suspense>
            {state.error && (
              <p className="text-red-500 text-sm">{state.error}</p>
            )}
            {state.success && (
              <p className="text-green-500 text-sm">{state.success}</p>
            )}
            <Button
              type="submit"
              className="bg-orange-500 hover:bg-orange-600 text-white"
              disabled={isPending}
            >
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Demo Payment Gateway Test Section */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Payment Gateway Test (Demo)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              This is a demo payment button to test the PhonePe integration. 
              Click below to initiate a test payment.
            </p>
            
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm text-amber-800 font-medium mb-2">Test Credentials:</p>
              <ul className="text-sm text-amber-700 space-y-1">
                <li>• UPI: <code className="bg-amber-100 px-1 rounded">success@paytm</code> (for success)</li>
                <li>• Card: <code className="bg-amber-100 px-1 rounded">4242 4242 4242 4242</code></li>
                <li>• CVV: <code className="bg-amber-100 px-1 rounded">123</code>, OTP: <code className="bg-amber-100 px-1 rounded">123456</code></li>
              </ul>
            </div>

            <div className="flex gap-4">
              <PaymentButton
                planId="STARTER"
                planName="Test Payment - Starter"
                amount={100}  // ₹100 for testing
                teamId="test_team_demo"
                className="bg-green-600 hover:bg-green-700"
              />
              
              <PaymentButton
                planId="PROFESSIONAL"
                planName="Test Payment - Professional"
                amount={500}  // ₹500 for testing
                teamId="test_team_demo"
                className="bg-blue-600 hover:bg-blue-700"
              />
            </div>

            <p className="text-xs text-gray-500 mt-4">
              Note: This is using PhonePe sandbox environment. No real money will be charged.
            </p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
