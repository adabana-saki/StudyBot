"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { getMyAchievements, UserAchievement } from "@/lib/api";
import AchievementCard from "@/components/AchievementCard";

export default function AchievementsPage() {
  const router = useRouter();
  const [achievements, setAchievements] = useState<UserAchievement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const data = await getMyAchievements();
        setAchievements(data);
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

  // Extract unique categories
  const allCategories = Array.from(
    new Set(achievements.map((a) => a.achievement.category))
  );

  // Filter achievements
  const filteredAchievements =
    filter === "all"
      ? achievements
      : filter === "unlocked"
        ? achievements.filter((a) => a.unlocked)
        : filter === "locked"
          ? achievements.filter((a) => !a.unlocked)
          : achievements.filter((a) => a.achievement.category === filter);

  // Sort: unlocked first, then by progress
  const sortedAchievements = [...filteredAchievements].sort((a, b) => {
    if (a.unlocked && !b.unlocked) return -1;
    if (!a.unlocked && b.unlocked) return 1;
    return b.progress / b.achievement.threshold - a.progress / a.achievement.threshold;
  });

  const unlockedCount = achievements.filter((a) => a.unlocked).length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blurple"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-gray-800 rounded-xl p-8 border border-red-600/50 max-w-md w-full text-center">
          <span className="text-4xl block mb-4">⚠️</span>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">実績</h1>
          <p className="text-gray-400 mt-1">
            {unlockedCount} / {achievements.length} 解除済み
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setFilter("all")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === "all"
              ? "bg-blurple text-white"
              : "bg-gray-800 text-gray-400 hover:text-white border border-gray-700"
          }`}
        >
          すべて ({achievements.length})
        </button>
        <button
          onClick={() => setFilter("unlocked")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === "unlocked"
              ? "bg-yellow-600 text-white"
              : "bg-gray-800 text-gray-400 hover:text-white border border-gray-700"
          }`}
        >
          解除済み ({unlockedCount})
        </button>
        <button
          onClick={() => setFilter("locked")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === "locked"
              ? "bg-gray-600 text-white"
              : "bg-gray-800 text-gray-400 hover:text-white border border-gray-700"
          }`}
        >
          未解除 ({achievements.length - unlockedCount})
        </button>
        {allCategories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === cat
                ? "bg-blurple text-white"
                : "bg-gray-800 text-gray-400 hover:text-white border border-gray-700"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Achievement Grid */}
      {sortedAchievements.length === 0 ? (
        <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 text-center">
          <p className="text-gray-400">実績が見つかりません</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedAchievements.map((item) => (
            <AchievementCard
              key={item.achievement.id}
              achievement={item.achievement}
              progress={item.progress}
              unlocked={item.unlocked}
            />
          ))}
        </div>
      )}
    </div>
  );
}
