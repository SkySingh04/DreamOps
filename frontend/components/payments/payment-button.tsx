"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface PaymentButtonProps {
  planId: string;
  planName: string;
  amount: number;
  teamId?: string;
  className?: string;
}

export function PaymentButton({
  planId,
  planName,
  amount,
  teamId,
  className
}: PaymentButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handlePayment = async () => {
    setIsLoading(true);

    try {
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
          team_id: teamId || "team_123", // Replace with actual team ID
          amount: amount * 100, // Convert to paise
          plan: planId.toUpperCase(),
          mobile_number: null, // Optional
          email: null, // Optional
          metadata: {
            plan_name: planName,
            initiated_from: "pricing_page"
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
          Processing...
        </>
      ) : (
        `Pay ₹${amount}`
      )}
    </Button>
  );
}