"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { getMyAchievements, UserAchievement } from "@/lib/api";
import AchievementCard from "@/components/AchievementCard";
import PageHeader from "@/components/PageHeader";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="border-destructive/50 max-w-md w-full">
          <CardContent className="p-8 text-center">
            <span className="text-4xl block mb-4">⚠️</span>
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="実績"
        description={`${unlockedCount} / ${achievements.length} 解除済み`}
      />

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 mb-6">
        <Button
          variant={filter === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("all")}
        >
          すべて ({achievements.length})
        </Button>
        <Button
          variant={filter === "unlocked" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("unlocked")}
          className={cn(filter === "unlocked" && "bg-yellow-600 hover:bg-yellow-700")}
        >
          解除済み ({unlockedCount})
        </Button>
        <Button
          variant={filter === "locked" ? "secondary" : "outline"}
          size="sm"
          onClick={() => setFilter("locked")}
        >
          未解除 ({achievements.length - unlockedCount})
        </Button>
        {allCategories.map((cat) => (
          <Button
            key={cat}
            variant={filter === cat ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(cat)}
          >
            {cat}
          </Button>
        ))}
      </div>

      {/* Achievement Grid */}
      {sortedAchievements.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground">実績が見つかりません</p>
          </CardContent>
        </Card>
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
