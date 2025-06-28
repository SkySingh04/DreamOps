import { Check } from 'lucide-react';
import { PaymentButton } from '@/components/payments/payment-button';

export default async function PricingPage() {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Choose Your Plan</h1>
        <p className="text-xl text-gray-600">Simple, transparent pricing</p>
        <p className="text-lg text-gray-500 mt-2">Dream easy while AI takes your on-call duty</p>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        <PricingCard
          name="Free"
          price="₹0"
          period="/month"
          planId="free"
          features={[
            '5 incidents per month',
            'Basic integrations',
            'Community support',
            '7-day data retention'
          ]}
          amount={0}
        />
        <PricingCard
          name="Starter"
          price="₹999"
          period="/month"
          planId="starter"
          features={[
            '50 incidents per month',
            'All integrations',
            'Email support',
            '30-day data retention',
            'Custom alert rules'
          ]}
          amount={999}
          popular={true}
        />
        <PricingCard
          name="Professional"
          price="₹4,999"
          period="/month"
          planId="professional"
          features={[
            'Unlimited incidents',
            'All integrations',
            'Priority support',
            '90-day data retention',
            'Advanced analytics',
            'Custom workflows'
          ]}
          amount={4999}
        />
      </div>
    </main>
  );
}

function PricingCard({
  name,
  price,
  period,
  planId,
  features,
  amount,
  popular = false,
}: {
  name: string;
  price: string;
  period?: string;
  planId: string;
  features: string[];
  amount: number;
  popular?: boolean;
}) {
  const isFreePlan = amount === 0;
  
  return (
    <div className={`relative pt-6 border rounded-lg p-6 bg-white shadow-sm ${popular ? 'border-orange-500 border-2' : ''}`}>
      {popular && (
        <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <span className="bg-orange-500 text-white px-3 py-1 text-sm font-medium rounded-full">
            Most Popular
          </span>
        </div>
      )}
      <h2 className="text-2xl font-medium text-gray-900 mb-2">{name}</h2>
      <p className="text-4xl font-medium text-gray-900 mb-1">
        {price}
        {period && <span className="text-lg text-gray-500">{period}</span>}
      </p>
      <ul className="space-y-4 mb-8 mt-6">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start">
            <Check className="h-5 w-5 text-orange-500 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-gray-700">{feature}</span>
          </li>
        ))}
      </ul>
      {isFreePlan ? (
        <div className="text-center py-3 px-6 rounded-md bg-gray-100 text-gray-600 font-medium">
          Current Plan
        </div>
      ) : (
        <PaymentButton
          planId={planId}
          planName={name}
          amount={amount}
          className="w-full"
        />
      )}
    </div>
  );
}



