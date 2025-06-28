"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface PaymentButtonProps {
  planId?: string;
  planName?: string;
  amount?: number;
  teamId?: string;
  userId?: string; // For new user-based model
  currentPlan?: string; // For determining upgrade options
  className?: string;
}

export function PaymentButton({
  planId,
  planName,
  amount,
  teamId,
  userId,
  currentPlan,
  className
}: PaymentButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handlePayment = async () => {
    setIsLoading(true);

    try {
      // Determine if this is upgrade mode or specific plan mode
      const isUpgradeMode = currentPlan && !planId;
      
      if (isUpgradeMode) {
        // Redirect to pricing/upgrade page for plan selection
        window.location.href = '/pricing';
        setIsLoading(false);
        return;
      }

      // Validate required props for specific plan payment
      if (!planId || !planName || !amount) {
        throw new Error("Missing required payment parameters");
      }

      // Call backend API to initiate payment
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const useMockPayments = process.env.NEXT_PUBLIC_USE_MOCK_PAYMENTS === "true";
      const endpoint = useMockPayments 
        ? `${baseUrl}/api/v1/mock-payments/initiate`
        : `${baseUrl}/api/v1/payments/initiate`;
      
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Add authorization header if you have auth token
          // "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          team_id: userId || teamId || "team_123", // Use userId first, fallback to teamId
          amount: amount * 100, // Convert to paise
          plan: planId.toUpperCase(),
          mobile_number: null, // Optional
          email: null, // Optional
          metadata: {
            plan_name: planName,
            initiated_from: "dashboard_general"
          }
        })
      });

      if (!response.ok) {
        throw new Error("Failed to initiate payment");
      }

      const data = await response.json();

      if (data.success && data.redirect_url) {
        // Redirect to PhonePe payment page
        window.location.href = data.redirect_url;
      } else {
        throw new Error(data.error || "Payment initiation failed");
      }
    } catch (error) {
      console.error("Payment error:", error);
      toast({
        title: "Payment Failed",
        description: error instanceof Error ? error.message : "Failed to initiate payment. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Determine button text based on mode
  const isUpgradeMode = currentPlan && !planId;
  const buttonText = isUpgradeMode 
    ? "Upgrade Plan" 
    : amount 
      ? `Pay ₹${amount}` 
      : "Continue";

  return (
    <Button
      onClick={handlePayment}
      disabled={isLoading}
      className={className}
      size="lg"
    >
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          {isUpgradeMode ? "Loading..." : "Processing..."}
        </>
      ) : (
        buttonText
      )}
    </Button>
  );
}