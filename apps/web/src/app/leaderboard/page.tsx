"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import { getLeaderboard, LeaderboardEntry } from "@/lib/api";
import LeaderboardTable from "@/components/LeaderboardTable";

const categories = [
  { value: "xp", label: "XP" },
  { value: "study_time", label: "学習時間" },
  { value: "tasks", label: "タスク" },
];

const periods = [
  { value: "weekly", label: "週間" },
  { value: "monthly", label: "月間" },
  { value: "all_time", label: "全期間" },
];

export default function LeaderboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState(
    searchParams.get("category") || "xp"
  );
  const [period, setPeriod] = useState(
    searchParams.get("period") || "all_time"
  );

  // Use guild_id from query param or a placeholder
  const guildId = searchParams.get("guild_id") || "default";

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getLeaderboard(guildId, category, period);
        setEntries(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "データの取得に失敗しました"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router, guildId, category, period]);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-white mb-8">リーダーボード</h1>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        {/* Category Tabs */}
        <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setCategory(cat.value)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                category === cat.value
                  ? "bg-blurple text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Period Selector */}
        <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700">
          {periods.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                period === p.value
                  ? "bg-blurple text-white"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blurple"></div>
        </div>
      ) : error ? (
        <div className="bg-gray-800 rounded-xl p-8 border border-red-600/50 text-center">
          <span className="text-4xl block mb-4">⚠️</span>
          <p className="text-gray-400">{error}</p>
        </div>
      ) : (
        <LeaderboardTable entries={entries} />
      )}
    </div>
  );
}
