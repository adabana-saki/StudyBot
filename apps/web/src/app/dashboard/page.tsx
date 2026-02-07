"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthenticated } from "@/lib/auth";
import {
  getProfile,
  getStudyStats,
  getDailyStudy,
  UserProfile,
  StudyStats,
  DailyStudy,
} from "@/lib/api";
import StatsCard from "@/components/StatsCard";
import StudyChart from "@/components/StudyChart";

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [studyStats, setStudyStats] = useState<StudyStats | null>(null);
  const [dailyStudy, setDailyStudy] = useState<DailyStudy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    async function fetchData() {
      try {
        const [profileData, statsData, dailyData] = await Promise.all([
          getProfile(),
          getStudyStats("weekly"),
          getDailyStudy(14),
        ]);
        setProfile(profileData);
        setStudyStats(statsData);
        setDailyStudy(dailyData);
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blurple mx-auto mb-4"></div>
          <p className="text-gray-400">読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="bg-gray-800 rounded-xl p-8 border border-red-600/50 max-w-md w-full text-center">
          <span className="text-4xl block mb-4">⚠️</span>
          <h1 className="text-xl font-bold text-white mb-2">エラー</h1>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">
          おかえりなさい{profile?.display_name ? `、${profile.display_name}` : ""}さん
        </h1>
        <p className="text-gray-400 mt-1">
          今日も頑張りましょう！
        </p>
      </div>

      {/* Profile Summary */}
      {profile && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 mb-8">
          <div className="flex items-center space-x-4">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={profile.display_name}
                className="w-16 h-16 rounded-full border-2 border-blurple"
              />
            ) : (
              <div className="w-16 h-16 rounded-full bg-blurple flex items-center justify-center text-2xl font-bold text-white">
                {profile.display_name.charAt(0)}
              </div>
            )}
            <div>
              <h2 className="text-xl font-bold text-white">
                {profile.display_name}
              </h2>
              <div className="flex items-center space-x-4 mt-1">
                <span className="text-sm text-blurple font-medium">
                  Lv.{profile.level}
                </span>
                <span className="text-sm text-gray-400">
                  ランク #{profile.rank}
                </span>
              </div>
              {/* XP Progress Bar */}
              <div className="mt-2 w-64">
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blurple h-2 rounded-full transition-all"
                    style={{
                      width: `${(profile.xp % 1000) / 10}%`,
                    }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {profile.xp.toLocaleString()} XP
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard
          icon="⏱️"
          label="総学習時間（週間）"
          value={
            studyStats
              ? `${Math.floor(studyStats.total_minutes / 60)}時間${studyStats.total_minutes % 60}分`
              : "-"
          }
          color="text-blue-400"
        />
        <StatsCard
          icon="📝"
          label="セッション数"
          value={studyStats?.session_count ?? "-"}
          color="text-green-400"
        />
        <StatsCard
          icon="🔥"
          label="連続学習日数"
          value={
            profile ? `${profile.streak_days}日` : "-"
          }
          color="text-orange-400"
        />
        <StatsCard
          icon="🪙"
          label="StudyCoins"
          value={
            profile
              ? profile.coins.toLocaleString()
              : "-"
          }
          color="text-yellow-400"
        />
      </div>

      {/* Study Chart */}
      {dailyStudy.length > 0 && <StudyChart data={dailyStudy} />}

      {/* Quick Links */}
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          href="/leaderboard"
          className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-blurple/50 transition-colors group"
        >
          <span className="text-2xl block mb-2">🏆</span>
          <h3 className="font-semibold text-white group-hover:text-blurple transition-colors">
            リーダーボード
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            サーバーランキングを確認
          </p>
        </Link>
        <Link
          href="/achievements"
          className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-blurple/50 transition-colors group"
        >
          <span className="text-2xl block mb-2">🎖️</span>
          <h3 className="font-semibold text-white group-hover:text-blurple transition-colors">
            実績
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            実績の進捗を確認
          </p>
        </Link>
        <Link
          href="/flashcards"
          className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-blurple/50 transition-colors group"
        >
          <span className="text-2xl block mb-2">🃏</span>
          <h3 className="font-semibold text-white group-hover:text-blurple transition-colors">
            フラッシュカード
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            カードを復習する
          </p>
        </Link>
      </div>
    </div>
  );
}
