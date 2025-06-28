"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Shield, Zap, Rocket, Crown } from "lucide-react";

interface AccountTierBadgeProps {
  tier: string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  className?: string;
}

const tierConfig = {
  free: {
    label: "Free",
    icon: Shield,
    className: "bg-gray-100 text-gray-800 hover:bg-gray-200",
    iconColor: "text-gray-600"
  },
  starter: {
    label: "Starter",
    icon: Zap,
    className: "bg-blue-100 text-blue-800 hover:bg-blue-200",
    iconColor: "text-blue-600"
  },
  pro: {
    label: "Pro",
    icon: Rocket,
    className: "bg-purple-100 text-purple-800 hover:bg-purple-200",
    iconColor: "text-purple-600"
  },
  enterprise: {
    label: "Enterprise",
    icon: Crown,
    className: "bg-amber-100 text-amber-800 hover:bg-amber-200",
    iconColor: "text-amber-600"
  }
};

const sizeConfig = {
  sm: {
    badge: "text-xs px-2 py-0.5",
    icon: "h-3 w-3"
  },
  md: {
    badge: "text-sm px-2.5 py-0.5",
    icon: "h-4 w-4"
  },
  lg: {
    badge: "text-base px-3 py-1",
    icon: "h-5 w-5"
  }
};

export function AccountTierBadge({ 
  tier = "free", 
  size = "md", 
  showIcon = true,
  className 
}: AccountTierBadgeProps) {
  const config = tierConfig[tier.toLowerCase() as keyof typeof tierConfig] || tierConfig.free;
  const Icon = config.icon;
  const sizeClasses = sizeConfig[size];

  return (
    <Badge 
      variant="secondary" 
      className={cn(
        config.className,
        sizeClasses.badge,
        "font-medium transition-colors",
        className
      )}
    >
      {showIcon && (
        <Icon className={cn(sizeClasses.icon, config.iconColor, "mr-1")} />
      )}
      {config.label}
    </Badge>
  );
}