import { Check } from 'lucide-react';

export default async function PricingPage() {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Pricing</h1>
        <p className="text-xl text-gray-600">Stripe integration has been removed</p>
        <p className="text-lg text-gray-500 mt-2">This is now a simplified OnCall Agent dashboard</p>
      </div>
      
      <div className="grid md:grid-cols-2 gap-8 max-w-xl mx-auto">
        <PricingCard
          name="OnCall Agent"
          price="Free"
          features={[
            'AI-Powered Incident Response',
            'Kubernetes Integration',
            'GitHub MCP Support',
            'PagerDuty Webhooks',
            'Real-time Monitoring'
          ]}
        />
        <PricingCard
          name="Enterprise"
          price="Contact Us"
          features={[
            'Everything in Free, and:',
            'Custom Integrations',
            'Priority Support',
            'Advanced Analytics',
            'Multi-tenant Support'
          ]}
        />
      </div>
    </main>
  );
}

function PricingCard({
  name,
  price,
  features,
}: {
  name: string;
  price: string;
  features: string[];
}) {
  return (
    <div className="pt-6 border rounded-lg p-6 bg-white shadow-sm">
      <h2 className="text-2xl font-medium text-gray-900 mb-2">{name}</h2>
      <p className="text-4xl font-medium text-gray-900 mb-6">
        {price}
      </p>
      <ul className="space-y-4 mb-8">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start">
            <Check className="h-5 w-5 text-orange-500 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-gray-700">{feature}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}



