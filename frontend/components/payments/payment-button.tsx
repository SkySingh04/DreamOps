'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Zap, Loader2 } from 'lucide-react'

interface PaymentButtonProps {
  planId?: string
  planName?: string
  amount?: number
  userId?: string
  currentPlan?: string
  className?: string
}

export function PaymentButton({
  planId,
  planName,
  amount,
  userId,
  currentPlan,
  className
}: PaymentButtonProps) {
  const [loading, setLoading] = useState(false)

  const handleUpgrade = async () => {
    setLoading(true)
    try {
      // Placeholder for payment integration
      // This would typically redirect to a payment provider or open a checkout modal
      console.log('Upgrading to plan:', { planId, planName, amount, userId })

      // Simulate a brief delay
      await new Promise(resolve => setTimeout(resolve, 1000))

      // For now, just show an alert
      alert(`Payment integration coming soon! Plan: ${planName || 'Pro'} - $${amount || 49}/month`)
    } catch (error) {
      console.error('Payment error:', error)
    } finally {
      setLoading(false)
    }
  }

  // If user is already on a paid plan
  if (currentPlan && currentPlan !== 'free') {
    return (
      <Button className={className} variant="outline" disabled>
        Current Plan: {currentPlan}
      </Button>
    )
  }

  return (
    <Button
      className={className}
      onClick={handleUpgrade}
      disabled={loading}
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          Processing...
        </>
      ) : (
        <>
          <Zap className="h-4 w-4 mr-2" />
          {planName ? `Upgrade to ${planName}` : 'Upgrade Plan'}
        </>
      )}
    </Button>
  )
}
