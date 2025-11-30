'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Check, Zap, TrendingUp } from 'lucide-react'

interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  currentPlan: string
  alertsUsed: number
  alertsLimit: number
  teamId?: string
}

export function UpgradeModal({
  isOpen,
  onClose,
  currentPlan,
  alertsUsed,
  alertsLimit,
  teamId
}: UpgradeModalProps) {
  const plans = [
    {
      name: 'Pro',
      price: '$49',
      period: '/month',
      alerts: 100,
      features: ['100 alerts/month', 'Priority support', 'Advanced analytics', 'Custom integrations']
    },
    {
      name: 'Enterprise',
      price: '$199',
      period: '/month',
      alerts: 'Unlimited',
      features: ['Unlimited alerts', '24/7 support', 'SLA guarantee', 'Custom deployment', 'Dedicated account manager']
    }
  ]

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            Upgrade Your Plan
          </DialogTitle>
          <DialogDescription>
            You've used {alertsUsed} of {alertsLimit} alerts. Upgrade to continue monitoring.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 md:grid-cols-2 mt-4">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className="border rounded-lg p-4 hover:border-primary transition-colors"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-lg">{plan.name}</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold">{plan.price}</span>
                    <span className="text-gray-500">{plan.period}</span>
                  </div>
                </div>
                <Badge variant="secondary">{plan.alerts} alerts</Badge>
              </div>

              <ul className="space-y-2 mb-4">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-500" />
                    {feature}
                  </li>
                ))}
              </ul>

              <Button className="w-full" variant="default">
                <Zap className="h-4 w-4 mr-2" />
                Upgrade to {plan.name}
              </Button>
            </div>
          ))}
        </div>

        <p className="text-sm text-gray-500 text-center mt-4">
          Current plan: <span className="font-medium capitalize">{currentPlan}</span>
        </p>
      </DialogContent>
    </Dialog>
  )
}
