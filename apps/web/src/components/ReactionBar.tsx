"use client";

import { cn } from "@/lib/utils";
import { addReaction, removeReaction } from "@/lib/api";

const REACTION_TYPES = {
  applaud: "👏",
  fire: "🔥",
  heart: "❤️",
  study_on: "📚",
} as const;

interface ReactionBarProps {
  eventId: number;
  reactionCounts: Record<string, number>;
  myReactions: string[];
  onReactionChange: (
    newCounts: Record<string, number>,
    newMyReactions: string[]
  ) => void;
}

export default function ReactionBar({
  eventId,
  reactionCounts,
  myReactions,
  onReactionChange,
}: ReactionBarProps) {
  const handleToggle = async (type: string) => {
    const isActive = myReactions.includes(type);

    try {
      if (isActive) {
        await removeReaction(eventId, type);
        const newCounts = { ...reactionCounts };
        newCounts[type] = Math.max(0, (newCounts[type] || 0) - 1);
        if (newCounts[type] === 0) delete newCounts[type];
        onReactionChange(newCounts, myReactions.filter((r) => r !== type));
      } else {
        await addReaction(eventId, type);
        const newCounts = { ...reactionCounts };
        newCounts[type] = (newCounts[type] || 0) + 1;
        onReactionChange(newCounts, [...myReactions, type]);
      }
    } catch {
      // Silently ignore errors
    }
  };

  return (
    <div className="flex gap-1.5">
      {Object.entries(REACTION_TYPES).map(([type, emoji]) => {
        const count = reactionCounts[type] || 0;
        const isActive = myReactions.includes(type);

        return (
          <button
            key={type}
            onClick={() => handleToggle(type)}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border transition-colors",
              isActive
                ? "bg-primary/20 border-primary text-primary"
                : "bg-card border-border text-muted-foreground hover:border-primary/50"
            )}
          >
            <span>{emoji}</span>
            {count > 0 && <span>{count}</span>}
          </button>
        );
      })}
    </div>
  );
}
