"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface BuddyCardProps {
  username: string;
  subjects: string[];
  compatibilityScore: number;
  status: string;
}

export default function BuddyCard({ username, subjects, compatibilityScore, status }: BuddyCardProps) {
  return (
    <Card>
      <CardContent className="py-4 flex items-center gap-4">
        <div className="w-10 h-10 rounded-full bg-pink-500/20 flex items-center justify-center text-lg font-bold">
          {username.charAt(0)}
        </div>
        <div className="flex-1">
          <p className="font-medium">{username}</p>
          <p className="text-sm text-muted-foreground">
            {subjects.join(", ") || "教科未設定"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold">{Math.round(compatibilityScore * 100)}%</p>
          <Badge variant={status === "active" ? "default" : "secondary"} className="text-xs">
            {status === "active" ? "アクティブ" : status}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
