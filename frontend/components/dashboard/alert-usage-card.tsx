"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, TrendingUp, Zap } from "lucide-react";
import { UpgradeModal } from "@/components/payments/upgrade-modal";

interface AlertUsageData {
  alerts_used: number;
  alerts_limit: number;
  alerts_remaining: number;
  account_tier: string;
  billing_cycle_end: string;
  is_limit_reached: boolean;
}

interface AlertUsageCardProps {
  userId?: string;
  teamId?: string; // Keep for backward compatibility
  className?: string;
}

export function AlertUsageCard({ userId, teamId, className }: AlertUsageCardProps) {
  const [usageData, setUsageData] = useState<AlertUsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  useEffect(() => {
    fetchUsageData();
    // Refresh usage data every 30 seconds
    const interval = setInterval(fetchUsageData, 30000);
    return () => clearInterval(interval);
  }, [userId, teamId]);

  const fetchUsageData = async () => {
    try {
      // Use userId if available (new user-based model), otherwise fall back to teamId
      const id = userId || teamId || "team_123";
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/alert-tracking/usage/${id}`
      );
      if (response.ok) {
        const data = await response.json();
        setUsageData(data);
      }
    } catch (error) {
      console.error("Failed to fetch alert usage:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !usageData) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-1/3"></div>
            <div className="h-8 bg-gray-200 rounded w-full"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const usagePercentage = (usageData.alerts_used / usageData.alerts_limit) * 100;
  const daysUntilReset = Math.ceil(
    (new Date(usageData.billing_cycle_end).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );

  const tierColors = {
    free: "bg-gray-100 text-gray-800",
    starter: "bg-blue-100 text-blue-800",
    pro: "bg-purple-100 text-purple-800",
    enterprise: "bg-amber-100 text-amber-800"
  } as const;

  const tierIcons = {
    free: <AlertCircle className="h-4 w-4" />,
    starter: <Zap className="h-4 w-4" />,
    pro: <TrendingUp className="h-4 w-4" />,
    enterprise: <Zap className="h-4 w-4" />
  } as const;

  // Safely get tier values with fallback
  const getTierColor = (tier: string) => {
    return tierColors[tier as keyof typeof tierColors] || tierColors.free;
  };

  const getTierIcon = (tier: string) => {
    return tierIcons[tier as keyof typeof tierIcons] || tierIcons.free;
  };

  return (
    <>
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-medium">Alert Usage</CardTitle>
            <Badge className={getTierColor(usageData.account_tier)}>
              <span className="flex items-center gap-1">
                {getTierIcon(usageData.account_tier)}
                {usageData.account_tier.charAt(0).toUpperCase() + usageData.account_tier.slice(1)}
              </span>
            </Badge>
          </div>
          <CardDescription>
            {usageData.alerts_remaining} alerts remaining • Resets in {daysUntilReset} days
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl font-bold">
                  {usageData.alerts_used}/{usageData.alerts_limit}
                </span>
                <span className="text-sm text-muted-foreground">
                  {Math.round(usagePercentage)}% used
                </span>
              </div>
              <Progress 
                value={usagePercentage} 
                className={`h-2 ${usagePercentage > 80 ? "[&>div]:bg-red-500" : ""}`}
              />
            </div>

            {usageData.is_limit_reached && (
              <div className="p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-800 dark:text-red-200">
                  You've reached your monthly alert limit. Upgrade to continue receiving alerts.
                </p>
              </div>
            )}

            {(usageData.is_limit_reached || (usageData.account_tier === 'free' && usagePercentage >= 100)) && (
              <Button 
                onClick={() => setShowUpgradeModal(true)}
                className="w-full"
                variant="default"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Upgrade Plan
              </Button>
            )}
            
            {!usageData.is_limit_reached && usageData.account_tier === 'free' && usagePercentage > 60 && usagePercentage < 100 && (
              <Button 
                onClick={() => setShowUpgradeModal(true)}
                className="w-full"
                variant="outline"
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                View Plans
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        currentPlan={usageData.account_tier}
        alertsUsed={usageData.alerts_used}
        alertsLimit={usageData.alerts_limit}
        teamId={userId || teamId}
      />
    </>
  );
}