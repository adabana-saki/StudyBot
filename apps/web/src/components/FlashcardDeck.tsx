"use client";

import { useState } from "react";
import { Flashcard } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface FlashcardDeckProps {
  cards: Flashcard[];
  onReview: (cardId: string, quality: number) => void;
}

const qualityLabels = [
  { value: 1, label: "全然わからない", variant: "destructive" as const },
  { value: 2, label: "難しい", className: "bg-orange-600 hover:bg-orange-700 text-white" },
  { value: 3, label: "普通", className: "bg-yellow-600 hover:bg-yellow-700 text-white" },
  { value: 4, label: "簡単", className: "bg-green-600 hover:bg-green-700 text-white" },
  { value: 5, label: "完璧", className: "bg-emerald-600 hover:bg-emerald-700 text-white" },
];

export default function FlashcardDeck({ cards, onReview }: FlashcardDeckProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [completed, setCompleted] = useState(false);

  if (cards.length === 0) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <span className="text-4xl block mb-4">🎉</span>
          <p className="text-xl font-semibold">復習カードはありません</p>
          <p className="text-muted-foreground mt-2">
            すべてのカードを復習済みです。素晴らしい！
          </p>
        </CardContent>
      </Card>
    );
  }

  if (completed) {
    return (
      <Card>
        <CardContent className="p-8 text-center">
          <span className="text-4xl block mb-4">✅</span>
          <p className="text-xl font-semibold">復習完了！</p>
          <p className="text-muted-foreground mt-2">
            {cards.length}枚のカードを復習しました。お疲れ様でした！
          </p>
        </CardContent>
      </Card>
    );
  }

  const currentCard = cards[currentIndex];

  const handleReview = (quality: number) => {
    onReview(currentCard.id, quality);
    setFlipped(false);

    if (currentIndex + 1 < cards.length) {
      setCurrentIndex(currentIndex + 1);
    } else {
      setCompleted(true);
    }
  };

  return (
    <div>
      {/* Progress indicator */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-muted-foreground">
          {currentIndex + 1} / {cards.length}
        </p>
        <div className="flex-1 mx-4">
          <Progress
            value={((currentIndex + 1) / cards.length) * 100}
            className="h-1.5"
          />
        </div>
      </div>

      {/* Flashcard */}
      <div
        className="flashcard-container cursor-pointer mb-6"
        onClick={() => setFlipped(!flipped)}
        style={{ minHeight: "240px" }}
      >
        <div className={`flashcard-inner ${flipped ? "flipped" : ""}`}>
          {/* Front */}
          <div className="flashcard-front rounded-lg border bg-card p-8 flex items-center justify-center">
            <div className="text-center">
              <p className="text-xs text-muted-foreground uppercase tracking-wide mb-3">
                問題
              </p>
              <p className="text-xl font-medium">
                {currentCard.front}
              </p>
              <p className="text-xs text-muted-foreground mt-4">
                クリックして答えを表示
              </p>
            </div>
          </div>

          {/* Back */}
          <div className="flashcard-back rounded-lg border border-primary/50 bg-card p-8 flex items-center justify-center">
            <div className="text-center">
              <p className="text-xs text-primary uppercase tracking-wide mb-3">
                答え
              </p>
              <p className="text-xl font-medium">
                {currentCard.back}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quality rating buttons */}
      {flipped && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground text-center">
            理解度を評価してください
          </p>
          <div className="grid grid-cols-5 gap-2">
            {qualityLabels.map(({ value, label, variant, className }) => (
              <Button
                key={value}
                onClick={() => handleReview(value)}
                variant={variant || "default"}
                size="sm"
                className={cn("px-2 py-3 h-auto text-xs", className)}
              >
                {label}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
