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
import PageHeader from "@/components/PageHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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
    return <LoadingSpinner />;
  }

  // Study mode
  if (studyDeckId) {
    const currentDeck = decks.find((d) => d.id === studyDeckId);
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={exitStudy}
            className="text-muted-foreground mb-2"
          >
            ← デッキ一覧に戻る
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">
            {currentDeck?.name || "復習"}
          </h1>
        </div>

        {studyLoading ? (
          <LoadingSpinner label="カードを読み込み中..." />
        ) : (
          <FlashcardDeck cards={reviewCards} onReview={handleReview} />
        )}
      </div>
    );
  }

  // Deck list
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title="フラッシュカード" />

      {error && (
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      )}

      {decks.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <span className="text-4xl block mb-4">🃏</span>
            <p className="text-xl font-semibold mb-2">
              デッキがありません
            </p>
            <p className="text-muted-foreground">
              Discordで <code className="text-primary">/flashcard create</code>{" "}
              コマンドを使ってデッキを作成してください。
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {decks.map((deck) => (
            <Card
              key={deck.id}
              className="hover:border-muted-foreground/30 transition-colors"
            >
              <CardHeader>
                <CardTitle className="text-lg truncate">
                  {deck.name}
                </CardTitle>
                {deck.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {deck.description}
                  </p>
                )}
              </CardHeader>
              <CardContent>
                <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                  <span>カード: {deck.card_count}枚</span>
                  <span
                    className={
                      deck.due_count > 0 ? "text-orange-400 font-medium" : ""
                    }
                  >
                    復習待ち: {deck.due_count}枚
                  </span>
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  onClick={() => startStudy(deck.id)}
                  disabled={deck.due_count === 0}
                  variant={deck.due_count > 0 ? "default" : "secondary"}
                  className="w-full"
                >
                  {deck.due_count > 0
                    ? `復習する (${deck.due_count}枚)`
                    : "復習するカードはありません"}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
