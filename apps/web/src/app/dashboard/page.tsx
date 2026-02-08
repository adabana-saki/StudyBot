"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { isAuthenticated } from "@/lib/auth";
import {
  getProfile,
  getStudyStats,
  getDailyStudy,
  getActiveSessions,
  UserProfile,
  StudyStats,
  DailyStudy,
  ActiveSession,
} from "@/lib/api";
import ActiveSessionCard from "@/components/ActiveSessionCard";
import StatsCard from "@/components/StatsCard";
import StudyChart from "@/components/StudyChart";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [studyStats, setStudyStats] = useState<StudyStats | null>(null);
  const [dailyStudy, setDailyStudy] = useState<DailyStudy[]>([]);
  const [activeSessions, setActiveSessions] = useState<ActiveSession[]>([]);
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
        const sessionsData = await getActiveSessions().catch(() => []);
        setActiveSessions(sessionsData);
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
    return <LoadingSpinner label="読み込み中..." />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="max-w-md w-full border-destructive/50">
          <CardContent className="pt-6 text-center">
            <span className="text-4xl block mb-4">⚠️</span>
            <h1 className="text-xl font-bold mb-2">エラー</h1>
            <p className="text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Header */}
      <PageHeader
        title={`おかえりなさい${profile?.display_name ? `、${profile.display_name}` : ""}さん`}
        description="今日も頑張りましょう！"
      />

      {/* Active Sessions */}
      {activeSessions.length > 0 && (
        <div className="mb-6 space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">アクティブセッション</h3>
          {activeSessions.map((s) => (
            <ActiveSessionCard key={s.id} session={s} />
          ))}
        </div>
      )}

      {/* Profile Summary */}
      {profile && (
        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-4">
              {profile.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={profile.display_name}
                  className="w-16 h-16 rounded-full border-2 border-primary"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-2xl font-bold text-primary-foreground">
                  {profile.display_name.charAt(0)}
                </div>
              )}
              <div>
                <h2 className="text-xl font-bold">
                  {profile.display_name}
                </h2>
                <div className="flex items-center space-x-3 mt-1">
                  <Badge>Lv.{profile.level}</Badge>
                  <span className="text-sm text-muted-foreground">
                    ランク #{profile.rank}
                  </span>
                </div>
                {/* XP Progress Bar */}
                <div className="mt-2 w-64">
                  <Progress
                    value={(profile.xp % 1000) / 10}
                    className="h-2"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {profile.xp.toLocaleString()} XP
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
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
        <Link href="/leaderboard">
          <Card className="hover:border-primary/50 transition-colors group h-full">
            <CardContent className="pt-6">
              <span className="text-2xl block mb-2">🏆</span>
              <h3 className="font-semibold group-hover:text-primary transition-colors">
                リーダーボード
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                サーバーランキングを確認
              </p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/achievements">
          <Card className="hover:border-primary/50 transition-colors group h-full">
            <CardContent className="pt-6">
              <span className="text-2xl block mb-2">🎖️</span>
              <h3 className="font-semibold group-hover:text-primary transition-colors">
                実績
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                実績の進捗を確認
              </p>
            </CardContent>
          </Card>
        </Link>
        <Link href="/flashcards">
          <Card className="hover:border-primary/50 transition-colors group h-full">
            <CardContent className="pt-6">
              <span className="text-2xl block mb-2">🃏</span>
              <h3 className="font-semibold group-hover:text-primary transition-colors">
                フラッシュカード
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                カードを復習する
              </p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
