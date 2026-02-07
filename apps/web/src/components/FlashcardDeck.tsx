"use client";

import { useState } from "react";
import { Flashcard } from "@/lib/api";

interface FlashcardDeckProps {
  cards: Flashcard[];
  onReview: (cardId: string, quality: number) => void;
}

const qualityLabels = [
  { value: 1, label: "全然わからない", color: "bg-red-600 hover:bg-red-700" },
  { value: 2, label: "難しい", color: "bg-orange-600 hover:bg-orange-700" },
  { value: 3, label: "普通", color: "bg-yellow-600 hover:bg-yellow-700" },
  { value: 4, label: "簡単", color: "bg-green-600 hover:bg-green-700" },
  { value: 5, label: "完璧", color: "bg-emerald-600 hover:bg-emerald-700" },
];

export default function FlashcardDeck({ cards, onReview }: FlashcardDeckProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [completed, setCompleted] = useState(false);

  if (cards.length === 0) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <span className="text-4xl block mb-4">🎉</span>
        <p className="text-xl font-semibold text-white">復習カードはありません</p>
        <p className="text-gray-400 mt-2">
          すべてのカードを復習済みです。素晴らしい！
        </p>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
        <span className="text-4xl block mb-4">✅</span>
        <p className="text-xl font-semibold text-white">復習完了！</p>
        <p className="text-gray-400 mt-2">
          {cards.length}枚のカードを復習しました。お疲れ様でした！
        </p>
      </div>
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
        <p className="text-sm text-gray-400">
          {currentIndex + 1} / {cards.length}
        </p>
        <div className="flex-1 mx-4">
          <div className="w-full bg-gray-700 rounded-full h-1.5">
            <div
              className="bg-blurple h-1.5 rounded-full transition-all"
              style={{
                width: `${((currentIndex + 1) / cards.length) * 100}%`,
              }}
            />
          </div>
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
          <div className="flashcard-front bg-gray-800 rounded-xl border border-gray-700 p-8 flex items-center justify-center">
            <div className="text-center">
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-3">
                問題
              </p>
              <p className="text-xl text-white font-medium">
                {currentCard.front}
              </p>
              <p className="text-xs text-gray-500 mt-4">
                クリックして答えを表示
              </p>
            </div>
          </div>

          {/* Back */}
          <div className="flashcard-back bg-gray-800 rounded-xl border border-blurple/50 p-8 flex items-center justify-center">
            <div className="text-center">
              <p className="text-xs text-blurple uppercase tracking-wide mb-3">
                答え
              </p>
              <p className="text-xl text-white font-medium">
                {currentCard.back}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quality rating buttons */}
      {flipped && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400 text-center">
            理解度を評価してください
          </p>
          <div className="grid grid-cols-5 gap-2">
            {qualityLabels.map(({ value, label, color }) => (
              <button
                key={value}
                onClick={() => handleReview(value)}
                className={`${color} text-white px-2 py-3 rounded-lg text-xs font-medium transition-colors`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
