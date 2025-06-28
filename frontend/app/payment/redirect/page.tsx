"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function PaymentRedirectPage() {
  const searchParams = useSearchParams();
  const transactionId = searchParams.get("transaction_id");
  const [status, setStatus] = useState<"checking" | "success" | "failed">("checking");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!transactionId) {
      setStatus("failed");
      setMessage("Invalid transaction ID");
      return;
    }

    // Check payment status
    const checkStatus = async () => {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const useMockPayments = process.env.NEXT_PUBLIC_USE_MOCK_PAYMENTS === "true";
        const endpoint = useMockPayments 
          ? `${baseUrl}/api/v1/mock-payments/status`
          : `${baseUrl}/api/v1/payments/status`;
        
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // Add authorization header if needed
          },
          body: JSON.stringify({
            merchant_transaction_id: transactionId
          })
        });

        if (!response.ok) {
          throw new Error("Failed to check payment status");
        }

        const data = await response.json();

        if (data.success && data.payment_status === "SUCCESS") {
          setStatus("success");
          setMessage("Payment completed successfully!");
        } else {
          setStatus("failed");
          setMessage(data.message || "Payment failed");
        }
      } catch (error) {
        console.error("Error checking payment status:", error);
        setStatus("failed");
        setMessage("Failed to verify payment status");
      }
    };

    checkStatus();
  }, [transactionId]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Payment Status</CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {status === "checking" && (
            <div className="py-8">
              <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary mb-4" />
              <p className="text-gray-600">Verifying your payment...</p>
            </div>
          )}

          {status === "success" && (
            <div className="py-8">
              <CheckCircle className="h-12 w-12 mx-auto text-green-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">Payment Successful!</h3>
              <p className="text-gray-600 mb-6">{message}</p>
              <p className="text-sm text-gray-500 mb-6">
                Transaction ID: {transactionId}
              </p>
              <Link href="/dashboard">
                <Button className="w-full">Go to Dashboard</Button>
              </Link>
            </div>
          )}

          {status === "failed" && (
            <div className="py-8">
              <XCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">Payment Failed</h3>
              <p className="text-gray-600 mb-6">{message}</p>
              {transactionId && (
                <p className="text-sm text-gray-500 mb-6">
                  Transaction ID: {transactionId}
                </p>
              )}
              <div className="space-y-3">
                <Link href="/pricing" className="block">
                  <Button className="w-full">Try Again</Button>
                </Link>
                <Link href="/dashboard" className="block">
                  <Button variant="outline" className="w-full">
                    Back to Dashboard
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}