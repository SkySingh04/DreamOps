"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, X, Zap, Shield, Rocket, Crown } from "lucide-react";
import { PaymentButton } from "./payment-button";
import { useToast } from "@/components/ui/use-toast";

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlan?: string;
  alertsUsed?: number;
  alertsLimit?: number;
  teamId?: string;
}

interface Plan {
  id: string;
  name: string;
  displayName: string;
  price: number;
  currency: string;
  alertsLimit: number;
  features: string[];
  recommended?: boolean;
  icon: React.ReactNode;
  color: string;
}

const plans: Plan[] = [
  {
    id: "starter",
    name: "Starter",
    displayName: "Starter Plan",
    price: 999,
    currency: "INR",
    alertsLimit: 50,
    features: [
      "50 alerts per month",
      "All integrations",
      "Email support",
      "Alert history - 30 days",
      "Basic analytics"
    ],
    icon: <Zap className="h-5 w-5" />,
    color: "text-blue-600"
  },
  {
    id: "pro",
    name: "Pro",
    displayName: "Professional Plan",
    price: 2999,
    currency: "INR",
    alertsLimit: 200,
    features: [
      "200 alerts per month",
      "All integrations",
      "Priority support",
      "Alert history - 90 days",
      "Custom workflows",
      "Team collaboration",
      "Advanced analytics"
    ],
    recommended: true,
    icon: <Rocket className="h-5 w-5" />,
    color: "text-purple-600"
  },
  {
    id: "enterprise",
    name: "Enterprise",
    displayName: "Enterprise Plan",
    price: 9999,
    currency: "INR",
    alertsLimit: -1,
    features: [
      "Unlimited alerts",
      "All integrations",
      "24/7 phone support",
      "Unlimited alert history",
      "Custom integrations",
      "SLA guarantee",
      "Dedicated account manager",
      "On-premise deployment option"
    ],
    icon: <Crown className="h-5 w-5" />,
    color: "text-amber-600"
  }
];

export function UpgradeModal({
  isOpen,
  onClose,
  currentPlan = "free",
  alertsUsed = 0,
  alertsLimit = 3,
  teamId = "team_123"
}: UpgradeModalProps) {
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const { toast } = useToast();

  const handleUpgradeSuccess = (planId: string) => {
    toast({
      title: "Upgrade Successful!",
      description: `Your account has been upgraded to ${plans.find(p => p.id === planId)?.displayName}`,
    });
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl">Upgrade Your Plan</DialogTitle>
          <DialogDescription className="text-base">
            You've used {alertsUsed} out of {alertsLimit} alerts this month. 
            Upgrade to handle more incidents with AI-powered support.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {plans.map((plan) => (
            <Card 
              key={plan.id}
              className={`relative cursor-pointer transition-all ${
                selectedPlan === plan.id ? "ring-2 ring-primary" : ""
              } ${plan.recommended ? "scale-105 shadow-lg" : ""}`}
              onClick={() => setSelectedPlan(plan.id)}
            >
              {plan.recommended && (
                <Badge 
                  className="absolute -top-2 -right-2 bg-gradient-to-r from-purple-600 to-pink-600"
                >
                  Recommended
                </Badge>
              )}
              
              <CardHeader>
                <div className="flex items-center justify-between mb-2">
                  <div className={`${plan.color}`}>
                    {plan.icon}
                  </div>
                  {currentPlan === plan.id && (
                    <Badge variant="secondary">Current Plan</Badge>
                  )}
                </div>
                <CardTitle className="text-xl">{plan.displayName}</CardTitle>
                <CardDescription className="mt-2">
                  <span className="text-3xl font-bold">₹{plan.price}</span>
                  <span className="text-muted-foreground">/month</span>
                </CardDescription>
              </CardHeader>

              <CardContent>
                <div className="space-y-2">
                  <div className="font-semibold text-sm mb-2">
                    {plan.alertsLimit === -1 ? "Unlimited" : plan.alertsLimit} alerts/month
                  </div>
                  <ul className="space-y-2">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>

              <CardFooter>
                {currentPlan === plan.id ? (
                  <Button variant="secondary" disabled className="w-full">
                    Current Plan
                  </Button>
                ) : (
                  <PaymentButton
                    planId={plan.id}
                    planName={plan.displayName}
                    amount={plan.price}
                    teamId={teamId}
                    className="w-full"
                  />
                )}
              </CardFooter>
            </Card>
          ))}
        </div>

        <div className="mt-6 p-4 bg-muted rounded-lg">
          <h4 className="font-semibold mb-2">Why upgrade?</h4>
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>• Handle more incidents without interruption</li>
            <li>• Get priority support for critical issues</li>
            <li>• Access advanced features and integrations</li>
            <li>• Keep your team productive with AI-powered automation</li>
          </ul>
        </div>
      </DialogContent>
    </Dialog>
  );
}