"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { getServerStats, ServerStats } from "@/lib/api";

export default function ServerPage() {
  const authenticated = useAuthGuard();
  const [stats, setStats] = useState<ServerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guildId, setGuildId] = useState<string>("");

  useEffect(() => {
    if (!authenticated) return;
    const savedGuildId = localStorage.getItem("guild_id") || "";
    if (savedGuildId) {
      setGuildId(savedGuildId);
    } else {
      setLoading(false);
    }
  }, [authenticated]);

  useEffect(() => {
    if (guildId) {
      fetchStats();
    }
  }, [guildId]);

  async function fetchStats() {
    setLoading(true);
    try {
      const data = await getServerStats(guildId);
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }

  function formatMinutes(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) return `${hours}時間${mins}分`;
    return `${mins}分`;
  }

  if (loading) return <LoadingSpinner />;

  if (!guildId) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <PageHeader title="サーバー統計" />
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-muted-foreground mb-4">
              サーバーIDを入力して統計を表示します
            </p>
            <div className="flex items-center space-x-3 max-w-md mx-auto">
              <Input
                type="text"
                placeholder="サーバーID..."
                value={guildId}
                onChange={(e) => setGuildId(e.target.value)}
              />
              <Button
                onClick={() => {
                  if (guildId) {
                    localStorage.setItem("guild_id", guildId);
                    fetchStats();
                  }
                }}
              >
                表示
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <PageHeader title="サーバー統計" />

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {stats && (
        <div className="space-y-6">
          {/* Overview Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-muted-foreground">メンバー数</p>
                <p className="text-2xl font-bold mt-1">
                  {stats.member_count.toLocaleString()}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-muted-foreground">総学習時間</p>
                <p className="text-2xl font-bold text-blue-400 mt-1">
                  {formatMinutes(stats.total_minutes)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-muted-foreground">セッション数</p>
                <p className="text-2xl font-bold text-green-400 mt-1">
                  {stats.total_sessions.toLocaleString()}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 text-center">
                <p className="text-sm text-muted-foreground">週間アクティブ</p>
                <p className="text-2xl font-bold text-primary mt-1">
                  {stats.weekly_active_members}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Weekly Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">今週のサマリー</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-accent/50 rounded-lg p-4">
                  <p className="text-sm text-muted-foreground">週間学習時間</p>
                  <p className="text-xl font-bold text-blue-400 mt-1">
                    {formatMinutes(stats.weekly_minutes)}
                  </p>
                </div>
                <div className="bg-accent/50 rounded-lg p-4">
                  <p className="text-sm text-muted-foreground">完了タスク数</p>
                  <p className="text-xl font-bold text-green-400 mt-1">
                    {stats.tasks_completed.toLocaleString()}
                  </p>
                </div>
                <div className="bg-accent/50 rounded-lg p-4">
                  <p className="text-sm text-muted-foreground">完了レイド数</p>
                  <p className="text-xl font-bold text-purple-400 mt-1">
                    {stats.raids_completed.toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Server Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">サーバー情報</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableBody>
                  <TableRow>
                    <TableCell className="text-muted-foreground">サーバーID</TableCell>
                    <TableCell className="text-right font-mono text-sm">{guildId}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="text-muted-foreground">1人あたりの平均学習時間</TableCell>
                    <TableCell className="text-right">
                      {stats.member_count > 0
                        ? formatMinutes(
                            Math.round(stats.total_minutes / stats.member_count)
                          )
                        : "-"}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="text-muted-foreground">
                      1セッションあたりの平均時間
                    </TableCell>
                    <TableCell className="text-right">
                      {stats.total_sessions > 0
                        ? formatMinutes(
                            Math.round(stats.total_minutes / stats.total_sessions)
                          )
                        : "-"}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Change Server */}
          <div className="text-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                localStorage.removeItem("guild_id");
                setGuildId("");
                setStats(null);
              }}
            >
              サーバーを変更
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
