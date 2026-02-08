"use client";

import { cn } from "@/lib/utils";

interface StatsCardProps {
  icon: string;
  label: string;
  value: string | number;
  color?: string;
}

export default function StatsCard({
  icon,
  label,
  value,
  color = "text-primary",
}: StatsCardProps) {
  return (
    <div className="rounded-lg border bg-card p-6 hover:border-muted-foreground/30 transition-colors">
      <div className="flex items-center space-x-4">
        <span className="text-3xl">{icon}</span>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className={cn("text-2xl font-bold", color)}>{value}</p>
        </div>
      </div>
    </div>
  );
}
