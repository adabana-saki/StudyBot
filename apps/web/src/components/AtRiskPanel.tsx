"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AtRiskMember, createAction } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AtRiskPanelProps {
  members: AtRiskMember[];
  guildId: string;
}

export default function AtRiskPanel({ members, guildId }: AtRiskPanelProps) {
  const [sending, setSending] = useState<number | null>(null);
  const [sent, setSent] = useState<Set<number>>(new Set());

  const getRiskBadge = (score: number) => {
    if (score >= 0.7) return { label: "高リスク", variant: "destructive" as const };
    if (score >= 0.4) return { label: "中リスク", variant: "default" as const };
    return { label: "低リスク", variant: "secondary" as const };
  };

  const handleSendDM = async (member: AtRiskMember) => {
    setSending(member.user_id);
    try {
      await createAction(guildId, "send_dm", {
        user_id: member.user_id,
        message: `${member.username}さん、最近お見かけしません！最高${member.best_streak}日連続の記録をお持ちです。またStudyBotで学習を再開しませんか？`,
      });
      setSent((prev) => new Set(Array.from(prev).concat(member.user_id)));
    } catch {
      // ignore
    } finally {
      setSending(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">離脱リスクメンバー</CardTitle>
      </CardHeader>
      <CardContent>
        {members.length === 0 ? (
          <p className="text-sm text-muted-foreground">リスクメンバーはいません</p>
        ) : (
          <div className="space-y-2">
            {members.map((member) => {
              const risk = getRiskBadge(member.risk_score);
              return (
                <div key={member.user_id} className="flex items-center gap-3 py-2 border-b last:border-0">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{member.username}</span>
                      <Badge variant={risk.variant} className="text-xs">{risk.label}</Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      最高ストリーク: {member.best_streak}日 | 非活動: {member.days_inactive}日
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={sent.has(member.user_id) || sending === member.user_id}
                    onClick={() => handleSendDM(member)}
                  >
                    {sent.has(member.user_id) ? "送信済" : sending === member.user_id ? "送信中..." : "DM送信"}
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
