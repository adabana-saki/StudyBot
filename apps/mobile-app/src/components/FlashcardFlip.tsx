/**
 * FlashcardFlip - 3D flip card animation component.
 * Shows front/back of a flashcard with a smooth flip transition.
 */
import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  TouchableWithoutFeedback,
  Dimensions,
} from "react-native";
import { Colors } from "../constants/colors";

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const CARD_WIDTH = SCREEN_WIDTH - 48;
const CARD_HEIGHT = 280;

interface FlashcardFlipProps {
  front: string;
  back: string;
  isFlipped: boolean;
  onFlip: () => void;
}

export default function FlashcardFlip({
  front,
  back,
  isFlipped,
  onFlip,
}: FlashcardFlipProps) {
  const flipAnimation = useRef(new Animated.Value(0)).current;
  const [showBack, setShowBack] = useState(false);

  useEffect(() => {
    if (isFlipped) {
      Animated.spring(flipAnimation, {
        toValue: 1,
        friction: 8,
        tension: 10,
        useNativeDriver: true,
      }).start();
      // Show back content at midpoint of animation
      const timer = setTimeout(() => setShowBack(true), 150);
      return () => clearTimeout(timer);
    } else {
      Animated.spring(flipAnimation, {
        toValue: 0,
        friction: 8,
        tension: 10,
        useNativeDriver: true,
      }).start();
      const timer = setTimeout(() => setShowBack(false), 150);
      return () => clearTimeout(timer);
    }
  }, [isFlipped, flipAnimation]);

  const frontInterpolation = flipAnimation.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ["0deg", "90deg", "180deg"],
  });

  const backInterpolation = flipAnimation.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: ["180deg", "270deg", "360deg"],
  });

  const frontOpacity = flipAnimation.interpolate({
    inputRange: [0, 0.5, 0.5, 1],
    outputRange: [1, 1, 0, 0],
  });

  const backOpacity = flipAnimation.interpolate({
    inputRange: [0, 0.5, 0.5, 1],
    outputRange: [0, 0, 1, 1],
  });

  return (
    <TouchableWithoutFeedback onPress={onFlip}>
      <View style={styles.container}>
        {/* Front face */}
        <Animated.View
          style={[
            styles.card,
            styles.cardFront,
            {
              opacity: frontOpacity,
              transform: [{ perspective: 1000 }, { rotateY: frontInterpolation }],
            },
          ]}
        >
          <Text style={styles.sideLabel}>QUESTION</Text>
          <Text style={styles.cardText}>{front}</Text>
          <Text style={styles.tapHint}>Tap to reveal answer</Text>
        </Animated.View>

        {/* Back face */}
        <Animated.View
          style={[
            styles.card,
            styles.cardBack,
            {
              opacity: backOpacity,
              transform: [{ perspective: 1000 }, { rotateY: backInterpolation }],
            },
          ]}
        >
          <Text style={styles.sideLabel}>ANSWER</Text>
          <Text style={styles.cardText}>{showBack ? back : ""}</Text>
        </Animated.View>
      </View>
    </TouchableWithoutFeedback>
  );
}

const styles = StyleSheet.create({
  container: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    alignSelf: "center",
  },
  card: {
    position: "absolute",
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    borderRadius: 16,
    padding: 24,
    justifyContent: "center",
    alignItems: "center",
    backfaceVisibility: "hidden",
    borderWidth: 1,
  },
  cardFront: {
    backgroundColor: Colors.card,
    borderColor: Colors.primary + "40",
  },
  cardBack: {
    backgroundColor: "#1a2332",
    borderColor: Colors.accent + "40",
  },
  sideLabel: {
    position: "absolute",
    top: 16,
    left: 20,
    fontSize: 10,
    fontWeight: "700",
    letterSpacing: 1.5,
    color: Colors.textMuted,
  },
  cardText: {
    fontSize: 18,
    lineHeight: 28,
    color: Colors.textPrimary,
    textAlign: "center",
  },
  tapHint: {
    position: "absolute",
    bottom: 16,
    fontSize: 12,
    color: Colors.textDisabled,
  },
});
