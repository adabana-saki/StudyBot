"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Shield, Clock, Zap } from "lucide-react";

const MOTIVATION_MESSAGES = [
  "今は集中タイムです。目標に向かって頑張りましょう！",
  "このアプリは今ブロック中です。学習に戻りましょう！",
  "誘惑に負けない強い意志を持ちましょう！",
  "あなたの目標は何ですか？今はそれに集中する時間です。",
  "ブロック解除まであと少し。最後まで頑張りましょう！",
  "未来の自分に感謝されるような選択をしましょう。",
  "集中を続けることで、素晴らしい成果が待っています。",
];

const CATEGORY_LABELS: Record<string, { label: string; emoji: string }> = {
  sns: { label: "SNS", emoji: "📱" },
  games: { label: "ゲーム", emoji: "🎮" },
  entertainment: { label: "エンタメ", emoji: "🎬" },
  news: { label: "ニュース", emoji: "📰" },
};

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

interface BlockOverlayProps {
  remaining: number;
  totalSeconds: number;
  blockCategories: string[];
  blockMessage: string;
  challengeMode: string;
  onChallengeRequest: () => void;
  dismissedUntil: Date | null;
}

export default function BlockOverlay({
  remaining,
  totalSeconds,
  blockCategories,
  blockMessage,
  challengeMode,
  onChallengeRequest,
  dismissedUntil,
}: BlockOverlayProps) {
  const [motivationIdx, setMotivationIdx] = useState(0);
  const isDismissed = dismissedUntil ? new Date() < dismissedUntil : false;

  // モチベーションメッセージのローテーション
  useEffect(() => {
    if (isDismissed) return;
    const interval = setInterval(() => {
      setMotivationIdx((prev) => (prev + 1) % MOTIVATION_MESSAGES.length);
    }, 10000);
    return () => clearInterval(interval);
  }, [isDismissed]);

  // 一時解除中の場合はオーバーレイを非表示
  if (isDismissed) {
    return null;
  }

  const progress = totalSeconds > 0 ? ((totalSeconds - remaining) / totalSeconds) * 100 : 0;
  const displayMessage = blockMessage || MOTIVATION_MESSAGES[motivationIdx];

  return (
    <div className="fixed inset-0 z-50 bg-background/98 backdrop-blur-sm flex flex-col items-center justify-center p-6">
      {/* Shield Icon */}
      <div className="mb-8 relative">
        <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center">
          <Shield className="w-12 h-12 text-primary" />
        </div>
        <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
          <Clock className="w-4 h-4 text-white" />
        </div>
      </div>

      {/* Large Countdown */}
      <div className="text-6xl sm:text-7xl font-bold font-mono text-primary mb-4 tabular-nums">
        {formatTime(remaining)}
      </div>

      {/* Progress Bar */}
      <div className="w-full max-w-md h-2 bg-muted rounded-full mb-6 overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-1000"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Motivation Message */}
      <p className="text-lg text-muted-foreground text-center max-w-md mb-8 transition-opacity duration-500">
        {displayMessage}
      </p>

      {/* Block Categories */}
      {blockCategories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-8 justify-center">
          {blockCategories.map((cat) => {
            const info = CATEGORY_LABELS[cat];
            return (
              <Badge key={cat} variant="secondary" className="text-sm py-1 px-3">
                {info?.emoji} {info?.label || cat}
              </Badge>
            );
          })}
        </div>
      )}

      {/* Challenge Unlock Button */}
      {challengeMode !== "none" && (
        <Button
          variant="outline"
          size="lg"
          onClick={onChallengeRequest}
          className="gap-2"
        >
          <Zap className="h-4 w-4" />
          チャレンジで一時解除
        </Button>
      )}

      <p className="text-xs text-muted-foreground mt-4">
        フォーカスモード有効中
      </p>
    </div>
  );
}
