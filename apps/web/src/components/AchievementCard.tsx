"use client";

import { Achievement } from "@/lib/api";

interface AchievementCardProps {
  achievement: Achievement;
  progress: number;
  unlocked: boolean;
}

export default function AchievementCard({
  achievement,
  progress,
  unlocked,
}: AchievementCardProps) {
  const progressPercent = Math.min(
    (progress / achievement.threshold) * 100,
    100
  );
  const isInProgress = !unlocked && progress > 0;

  return (
    <div
      className={`rounded-xl p-5 border transition-all ${
        unlocked
          ? "bg-yellow-900/20 border-yellow-600/50 shadow-lg shadow-yellow-900/10"
          : isInProgress
            ? "bg-gray-800 border-gray-600"
            : "bg-gray-800/50 border-gray-700 opacity-60"
      }`}
    >
      <div className="flex items-start space-x-3">
        <span
          className={`text-3xl ${unlocked ? "" : "grayscale"}`}
        >
          {achievement.emoji}
        </span>
        <div className="flex-1 min-w-0">
          <h3
            className={`font-semibold text-sm ${
              unlocked ? "text-yellow-400" : "text-gray-300"
            }`}
          >
            {achievement.name}
          </h3>
          <p className="text-xs text-gray-400 mt-1">
            {achievement.description}
          </p>
        </div>
      </div>

      {/* Progress bar */}
      {!unlocked && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>
              {progress} / {achievement.threshold}
            </span>
            <span>{Math.round(progressPercent)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all ${
                isInProgress ? "bg-blurple" : "bg-gray-600"
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {unlocked && (
        <div className="mt-3">
          <span className="inline-block px-2 py-0.5 text-xs font-medium text-yellow-400 bg-yellow-900/30 rounded-full">
            解除済み
          </span>
        </div>
      )}
    </div>
  );
}
