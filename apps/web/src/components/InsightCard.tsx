"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface InsightCardProps {
  type: string;
  title: string;
  body: string;
  confidence: number;
}

const typeConfig: Record<string, { icon: string; color: string }> = {
  pattern: { icon: "📊", color: "border-l-blue-500" },
  improvement: { icon: "📈", color: "border-l-green-500" },
  achievement: { icon: "🏆", color: "border-l-yellow-500" },
  warning: { icon: "⚠️", color: "border-l-red-500" },
  general: { icon: "💡", color: "border-l-purple-500" },
};

export default function InsightCard({ type, title, body, confidence }: InsightCardProps) {
  const config = typeConfig[type] || typeConfig.general;

  return (
    <Card className={`border-l-4 ${config.color}`}>
      <CardContent className="py-4">
        <div className="flex items-start gap-3">
          <span className="text-2xl">{config.icon}</span>
          <div className="flex-1">
            <h3 className="font-semibold text-sm">{title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{body}</p>
            <div className="flex items-center gap-2 mt-2">
              <Progress value={confidence * 100} className="h-1.5 flex-1" />
              <span className="text-xs text-muted-foreground">
                {Math.round(confidence * 100)}%
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
