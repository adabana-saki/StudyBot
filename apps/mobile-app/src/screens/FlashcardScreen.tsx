/**
 * FlashcardScreen - Deck selection and card review with flip animation.
 * Supports quality rating (1-5) and progress tracking.
 */
import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from "react-native";
import { Colors } from "../constants/colors";
import { FLASHCARD_QUALITY } from "../constants/config";
import { useApiQuery, useApiMutation } from "../hooks/useApi";
import {
  getFlashcardDecks,
  getReviewCards,
  submitReview,
  FlashcardDeck,
  Flashcard,
  ReviewResult,
} from "../lib/api";
import FlashcardFlip from "../components/FlashcardFlip";
import ProgressBar from "../components/ProgressBar";

type ScreenMode = "decks" | "review";

export default function FlashcardScreen() {
  const [mode, setMode] = useState<ScreenMode>("decks");
  const [selectedDeck, setSelectedDeck] = useState<FlashcardDeck | null>(null);
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [reviewedCount, setReviewedCount] = useState(0);

  // Fetch decks
  const {
    data: decks,
    isLoading: decksLoading,
    error: decksError,
    refetch: refetchDecks,
  } = useApiQuery<FlashcardDeck[]>(() => getFlashcardDecks(), []);

  // Review mutation
  const { mutate: submitCardReview, isLoading: isSubmitting } =
    useApiMutation<ReviewResult, { cardId: string; quality: number }>(
      ({ cardId, quality }) => submitReview(cardId, quality),
      {
        onSuccess: () => {
          setIsFlipped(false);
          setReviewedCount((prev) => prev + 1);

          // Small delay before showing next card
          setTimeout(() => {
            if (currentIndex < cards.length - 1) {
              setCurrentIndex((prev) => prev + 1);
            } else {
              // All cards reviewed
              Alert.alert(
                "Session Complete!",
                `You reviewed ${cards.length} cards. Great work!`,
                [
                  {
                    text: "Back to Decks",
                    onPress: () => {
                      setMode("decks");
                      refetchDecks();
                    },
                  },
                ]
              );
            }
          }, 300);
        },
        onError: (error) => {
          Alert.alert("Error", error);
        },
      }
    );

  const startReview = useCallback(
    async (deck: FlashcardDeck) => {
      setSelectedDeck(deck);
      setCurrentIndex(0);
      setReviewedCount(0);
      setIsFlipped(false);

      try {
        const reviewCards = await getReviewCards(deck.id);
        if (reviewCards.length === 0) {
          Alert.alert(
            "No Cards Due",
            "All cards in this deck are up to date. Come back later!"
          );
          return;
        }
        setCards(reviewCards);
        setMode("review");
      } catch {
        Alert.alert("Error", "Failed to load review cards.");
      }
    },
    []
  );

  const handleRating = useCallback(
    (quality: number) => {
      if (isSubmitting || currentIndex >= cards.length) return;
      const card = cards[currentIndex];
      submitCardReview({ cardId: card.id, quality });
    },
    [currentIndex, cards, isSubmitting, submitCardReview]
  );

  const handleBackToDecks = useCallback(() => {
    if (reviewedCount > 0 && currentIndex < cards.length - 1) {
      Alert.alert(
        "End Review?",
        `You have ${cards.length - currentIndex - 1} cards remaining.`,
        [
          { text: "Continue", style: "cancel" },
          {
            text: "End Review",
            onPress: () => {
              setMode("decks");
              refetchDecks();
            },
          },
        ]
      );
    } else {
      setMode("decks");
      refetchDecks();
    }
  }, [reviewedCount, currentIndex, cards, refetchDecks]);

  // Deck list view
  if (mode === "decks") {
    return (
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
      >
        <Text style={styles.screenTitle}>Flashcard Decks</Text>
        <Text style={styles.screenSubtitle}>
          Select a deck to start reviewing
        </Text>

        {decksLoading && (
          <ActivityIndicator
            size="large"
            color={Colors.primary}
            style={styles.loader}
          />
        )}

        {decksError && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{decksError}</Text>
            <TouchableOpacity onPress={refetchDecks} style={styles.retryButton}>
              <Text style={styles.retryText}>Retry</Text>
            </TouchableOpacity>
          </View>
        )}

        {decks?.map((deck) => (
          <TouchableOpacity
            key={deck.id}
            style={styles.deckCard}
            onPress={() => startReview(deck)}
            activeOpacity={0.7}
          >
            <View style={styles.deckHeader}>
              <Text style={styles.deckName}>{deck.name}</Text>
              {deck.due_count > 0 && (
                <View style={styles.dueBadge}>
                  <Text style={styles.dueText}>{deck.due_count} due</Text>
                </View>
              )}
            </View>
            {deck.description && (
              <Text style={styles.deckDescription} numberOfLines={2}>
                {deck.description}
              </Text>
            )}
            <View style={styles.deckFooter}>
              <Text style={styles.deckStat}>
                {"\u{1F0CF}"} {deck.card_count} cards
              </Text>
              {deck.last_reviewed && (
                <Text style={styles.deckStat}>
                  Last: {new Date(deck.last_reviewed).toLocaleDateString()}
                </Text>
              )}
            </View>
          </TouchableOpacity>
        ))}

        {decks && decks.length === 0 && !decksLoading && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>{"\u{1F0CF}"}</Text>
            <Text style={styles.emptyTitle}>No Decks Yet</Text>
            <Text style={styles.emptyText}>
              Create flashcard decks via Discord using the /flashcard command.
            </Text>
          </View>
        )}
      </ScrollView>
    );
  }

  // Review view
  const currentCard = cards[currentIndex];
  const totalCards = cards.length;

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.reviewHeader}>
        <TouchableOpacity onPress={handleBackToDecks} activeOpacity={0.7}>
          <Text style={styles.backButton}>{"\u2190"} Back</Text>
        </TouchableOpacity>
        <Text style={styles.reviewDeckName}>{selectedDeck?.name}</Text>
        <Text style={styles.reviewCount}>
          {currentIndex + 1}/{totalCards}
        </Text>
      </View>

      {/* Progress */}
      <View style={styles.progressContainer}>
        <ProgressBar
          current={reviewedCount}
          max={totalCards}
          color={Colors.accent}
          height={4}
        />
      </View>

      {/* Card */}
      <View style={styles.cardContainer}>
        {currentCard && (
          <FlashcardFlip
            front={currentCard.front}
            back={currentCard.back}
            isFlipped={isFlipped}
            onFlip={() => setIsFlipped(!isFlipped)}
          />
        )}
      </View>

      {/* Rating buttons (shown when flipped) */}
      {isFlipped && (
        <View style={styles.ratingContainer}>
          <Text style={styles.ratingLabel}>How well did you know this?</Text>
          <View style={styles.ratingButtons}>
            <RatingButton
              label="Again"
              value={FLASHCARD_QUALITY.AGAIN}
              color={Colors.error}
              onPress={handleRating}
              disabled={isSubmitting}
            />
            <RatingButton
              label="Hard"
              value={FLASHCARD_QUALITY.HARD}
              color={Colors.warning}
              onPress={handleRating}
              disabled={isSubmitting}
            />
            <RatingButton
              label="Good"
              value={FLASHCARD_QUALITY.GOOD}
              color={Colors.info}
              onPress={handleRating}
              disabled={isSubmitting}
            />
            <RatingButton
              label="Easy"
              value={FLASHCARD_QUALITY.EASY}
              color={Colors.accent}
              onPress={handleRating}
              disabled={isSubmitting}
            />
            <RatingButton
              label="Perfect"
              value={FLASHCARD_QUALITY.PERFECT}
              color={Colors.accentDark}
              onPress={handleRating}
              disabled={isSubmitting}
            />
          </View>
        </View>
      )}

      {/* Flip hint when not flipped */}
      {!isFlipped && (
        <View style={styles.flipHintContainer}>
          <Text style={styles.flipHint}>Tap the card to reveal the answer</Text>
        </View>
      )}
    </View>
  );
}

function RatingButton({
  label,
  value,
  color,
  onPress,
  disabled,
}: {
  label: string;
  value: number;
  color: string;
  onPress: (value: number) => void;
  disabled: boolean;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.ratingButton,
        { borderColor: color + "60" },
        disabled && { opacity: 0.5 },
      ]}
      onPress={() => onPress(value)}
      disabled={disabled}
      activeOpacity={0.7}
    >
      <Text style={[styles.ratingButtonText, { color }]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  screenTitle: {
    fontSize: 24,
    fontWeight: "800",
    color: Colors.textPrimary,
    marginBottom: 4,
  },
  screenSubtitle: {
    fontSize: 14,
    color: Colors.textMuted,
    marginBottom: 20,
  },
  loader: {
    marginTop: 40,
  },
  errorContainer: {
    backgroundColor: Colors.error + "15",
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.error + "30",
  },
  errorText: {
    color: Colors.error,
    fontSize: 14,
    marginBottom: 8,
  },
  retryButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  retryText: {
    color: Colors.primary,
    fontWeight: "600",
  },
  deckCard: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    padding: 18,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  deckHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  deckName: {
    fontSize: 17,
    fontWeight: "700",
    color: Colors.textPrimary,
    flex: 1,
  },
  dueBadge: {
    backgroundColor: Colors.primary + "20",
    borderRadius: 8,
    paddingVertical: 3,
    paddingHorizontal: 10,
    marginLeft: 8,
  },
  dueText: {
    fontSize: 12,
    fontWeight: "600",
    color: Colors.primary,
  },
  deckDescription: {
    fontSize: 13,
    color: Colors.textMuted,
    lineHeight: 19,
    marginBottom: 10,
  },
  deckFooter: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  deckStat: {
    fontSize: 12,
    color: Colors.textDisabled,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 60,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: Colors.textPrimary,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: Colors.textMuted,
    textAlign: "center",
    lineHeight: 20,
    paddingHorizontal: 32,
  },
  // Review view styles
  reviewHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  backButton: {
    fontSize: 16,
    color: Colors.primary,
    fontWeight: "600",
  },
  reviewDeckName: {
    fontSize: 16,
    fontWeight: "700",
    color: Colors.textPrimary,
  },
  reviewCount: {
    fontSize: 14,
    color: Colors.textMuted,
    fontWeight: "600",
  },
  progressContainer: {
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  cardContainer: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  ratingContainer: {
    paddingHorizontal: 16,
    paddingBottom: 32,
  },
  ratingLabel: {
    fontSize: 14,
    color: Colors.textMuted,
    textAlign: "center",
    marginBottom: 12,
    fontWeight: "600",
  },
  ratingButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 6,
  },
  ratingButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    backgroundColor: Colors.card,
    borderWidth: 1.5,
    alignItems: "center",
  },
  ratingButtonText: {
    fontSize: 12,
    fontWeight: "700",
  },
  flipHintContainer: {
    paddingBottom: 40,
    alignItems: "center",
  },
  flipHint: {
    fontSize: 14,
    color: Colors.textDisabled,
  },
});
