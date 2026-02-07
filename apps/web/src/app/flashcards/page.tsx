"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  getDecks,
  getReviewCards,
  submitReview,
  FlashcardDeck as FlashcardDeckType,
  Flashcard,
} from "@/lib/api";
import FlashcardDeck from "@/components/FlashcardDeck";

export default function FlashcardsPage() {
  const router = useRouter();
  const [decks, setDecks] = useState<FlashcardDeckType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Study mode state
  const [studyDeckId, setStudyDeckId] = useState<string | null>(null);
  const [reviewCards, setReviewCards] = useState<Flashcard[]>([]);
  const [studyLoading, setStudyLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const data = await getDecks();
        setDecks(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "データの取得に失敗しました"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router]);

  const startStudy = async (deckId: string) => {
    setStudyLoading(true);
    setError(null);
    try {
      const cards = await getReviewCards(deckId, 10);
      setReviewCards(cards);
      setStudyDeckId(deckId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "カードの取得に失敗しました"
      );
    } finally {
      setStudyLoading(false);
    }
  };

  const handleReview = async (cardId: string, quality: number) => {
    try {
      await submitReview(cardId, quality);
    } catch {
      // Silently fail - review will be retried next time
    }
  };

  const exitStudy = () => {
    setStudyDeckId(null);
    setReviewCards([]);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blurple"></div>
      </div>
    );
  }

  // Study mode
  if (studyDeckId) {
    const currentDeck = decks.find((d) => d.id === studyDeckId);
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <button
              onClick={exitStudy}
              className="text-sm text-gray-400 hover:text-white transition-colors mb-2"
            >
              ← デッキ一覧に戻る
            </button>
            <h1 className="text-2xl font-bold text-white">
              {currentDeck?.name || "復習"}
            </h1>
          </div>
        </div>

        {studyLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blurple"></div>
          </div>
        ) : (
          <FlashcardDeck cards={reviewCards} onReview={handleReview} />
        )}
      </div>
    );
  }

  // Deck list
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-white mb-8">フラッシュカード</h1>

      {error && (
        <div className="bg-gray-800 rounded-xl p-4 border border-red-600/50 mb-6">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {decks.length === 0 ? (
        <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
          <span className="text-4xl block mb-4">🃏</span>
          <p className="text-xl font-semibold text-white mb-2">
            デッキがありません
          </p>
          <p className="text-gray-400">
            Discordで <code className="text-blurple">/flashcard create</code>{" "}
            コマンドを使ってデッキを作成してください。
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {decks.map((deck) => (
            <div
              key={deck.id}
              className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-gray-600 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-white truncate">
                    {deck.name}
                  </h3>
                  {deck.description && (
                    <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                      {deck.description}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-4 mt-4 text-sm text-gray-400">
                <span>カード: {deck.card_count}枚</span>
                <span
                  className={
                    deck.due_count > 0 ? "text-orange-400 font-medium" : ""
                  }
                >
                  復習待ち: {deck.due_count}枚
                </span>
              </div>

              <button
                onClick={() => startStudy(deck.id)}
                disabled={deck.due_count === 0}
                className={`mt-4 w-full py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  deck.due_count > 0
                    ? "bg-blurple hover:bg-blurple-dark text-white"
                    : "bg-gray-700 text-gray-500 cursor-not-allowed"
                }`}
              >
                {deck.due_count > 0
                  ? `復習する (${deck.due_count}枚)`
                  : "復習するカードはありません"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
