"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  getWellness,
  getWellnessAverages,
  logWellness,
  WellnessLog,
  WellnessAverages,
} from "@/lib/api";
import StatsCard from "@/components/StatsCard";
import WellnessChart from "@/components/WellnessChart";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const MOOD_EMOJIS = ["", "\uD83D\uDE2B", "\uD83D\uDE1F", "\uD83D\uDE10", "\uD83D\uDE42", "\uD83D\uDE04"];
const ENERGY_EMOJIS = ["", "\uD83E\uDEAB", "\uD83D\uDD0B", "\uD83D\uDD0B", "\uD83D\uDD0B", "\u26A1"];
const STRESS_EMOJIS = ["", "\uD83D\uDE0C", "\uD83D\uDE0A", "\uD83D\uDE10", "\uD83D\uDE30", "\uD83D\uDE31"];

function getAverageColor(value: number, invert: boolean = false): string {
  // For stress, higher is worse (invert colors)
  const effectiveValue = invert ? 6 - value : value;
  if (effectiveValue >= 4) return "text-green-400";
  if (effectiveValue >= 3) return "text-yellow-400";
  return "text-red-400";
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}

export default function WellnessPage() {
  const router = useRouter();
  const [logs, setLogs] = useState<WellnessLog[]>([]);
  const [averages, setAverages] = useState<WellnessAverages | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [mood, setMood] = useState(3);
  const [energy, setEnergy] = useState(3);
  const [stress, setStress] = useState(3);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [logsData, avgData] = await Promise.all([
        getWellness(14),
        getWellnessAverages(7),
      ]);
      setLogs(logsData);
      setAverages(avgData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "データの取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/");
      return;
    }

    fetchData();
  }, [router, fetchData]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await logWellness({ mood, energy, stress, note });
      setShowForm(false);
      setMood(3);
      setEnergy(3);
      setStress(3);
      setNote("");
      // Refresh data
      setLoading(true);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "記録の保存に失敗しました"
      );
    } finally {
      setSubmitting(false);
    }
  }

  // Get the last 7 days of data for the chart
  const chartData = logs.slice(0, 7);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error && logs.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="border-destructive/50 max-w-md w-full text-center">
          <CardContent className="p-8">
            <span className="text-4xl block mb-4">&#x26A0;&#xFE0F;</span>
            <h1 className="text-xl font-bold mb-2">エラー</h1>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button
              onClick={() => {
                setLoading(true);
                setError(null);
                fetchData();
              }}
            >
              再試行
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <PageHeader
        title="ウェルネス"
        description="心身の状態を記録して、健康を管理しましょう"
        action={
          <Button onClick={() => setShowForm(true)}>
            <span>+</span>
            <span className="ml-2">記録する</span>
          </Button>
        }
      />

      {/* Error Banner (non-blocking) */}
      {error && logs.length > 0 && (
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      )}

      {/* Wellness Check Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl">
                  ウェルネスチェック
                </CardTitle>
                <button
                  onClick={() => setShowForm(false)}
                  className="text-muted-foreground hover:text-foreground transition-colors text-xl"
                >
                  &#x2715;
                </button>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Mood */}
                <div>
                  <Label className="mb-2 block">
                    気分
                  </Label>
                  <div className="flex items-center justify-between bg-background rounded-lg p-3">
                    {[1, 2, 3, 4, 5].map((val) => (
                      <button
                        key={`mood-${val}`}
                        type="button"
                        onClick={() => setMood(val)}
                        className={cn(
                          "text-3xl p-2 rounded-lg transition-all",
                          mood === val
                            ? "bg-blue-600/30 ring-2 ring-blue-500 scale-110"
                            : "hover:bg-accent opacity-60 hover:opacity-100"
                        )}
                      >
                        {MOOD_EMOJIS[val]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Energy */}
                <div>
                  <Label className="mb-2 block">
                    エネルギー
                  </Label>
                  <div className="flex items-center justify-between bg-background rounded-lg p-3">
                    {[1, 2, 3, 4, 5].map((val) => (
                      <button
                        key={`energy-${val}`}
                        type="button"
                        onClick={() => setEnergy(val)}
                        className={cn(
                          "text-3xl p-2 rounded-lg transition-all",
                          energy === val
                            ? "bg-green-600/30 ring-2 ring-green-500 scale-110"
                            : "hover:bg-accent opacity-60 hover:opacity-100"
                        )}
                      >
                        {ENERGY_EMOJIS[val]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Stress */}
                <div>
                  <Label className="mb-2 block">
                    ストレス
                  </Label>
                  <div className="flex items-center justify-between bg-background rounded-lg p-3">
                    {[1, 2, 3, 4, 5].map((val) => (
                      <button
                        key={`stress-${val}`}
                        type="button"
                        onClick={() => setStress(val)}
                        className={cn(
                          "text-3xl p-2 rounded-lg transition-all",
                          stress === val
                            ? "bg-red-600/30 ring-2 ring-red-500 scale-110"
                            : "hover:bg-accent opacity-60 hover:opacity-100"
                        )}
                      >
                        {STRESS_EMOJIS[val]}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Note */}
                <div>
                  <Label className="mb-2 block">
                    メモ（任意）
                  </Label>
                  <Textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="今日の気分について..."
                    rows={3}
                    className="resize-none"
                  />
                </div>

                {/* Submit */}
                <div className="flex justify-end space-x-3">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setShowForm(false)}
                  >
                    キャンセル
                  </Button>
                  <Button
                    type="submit"
                    disabled={submitting}
                  >
                    {submitting ? "保存中..." : "記録する"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Averages Cards */}
      {averages && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <StatsCard
            icon={MOOD_EMOJIS[Math.round(averages.avg_mood)] || "\uD83D\uDE10"}
            label="平均気分（7日間）"
            value={averages.avg_mood.toFixed(1)}
            color={getAverageColor(averages.avg_mood)}
          />
          <StatsCard
            icon={ENERGY_EMOJIS[Math.round(averages.avg_energy)] || "\uD83D\uDD0B"}
            label="平均エネルギー（7日間）"
            value={averages.avg_energy.toFixed(1)}
            color={getAverageColor(averages.avg_energy)}
          />
          <StatsCard
            icon={STRESS_EMOJIS[Math.round(averages.avg_stress)] || "\uD83D\uDE10"}
            label="平均ストレス（7日間）"
            value={averages.avg_stress.toFixed(1)}
            color={getAverageColor(averages.avg_stress, true)}
          />
        </div>
      )}

      {/* 7-Day Trend Chart */}
      {chartData.length > 0 && (
        <div className="mb-8">
          <WellnessChart data={chartData} />
        </div>
      )}

      {/* Recent Logs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">最近の記録</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {logs.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <span className="text-4xl block mb-4">&#x1F4DD;</span>
              <p className="text-muted-foreground">
                まだ記録がありません。上のボタンから記録してみましょう！
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>日時</TableHead>
                  <TableHead>気分</TableHead>
                  <TableHead>エネルギー</TableHead>
                  <TableHead>ストレス</TableHead>
                  <TableHead>メモ</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap">
                      {formatDate(log.logged_at)}
                    </TableCell>
                    <TableCell>
                      <span className="text-lg mr-1">
                        {MOOD_EMOJIS[log.mood]}
                      </span>
                      <span>{log.mood}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-lg mr-1">
                        {ENERGY_EMOJIS[log.energy]}
                      </span>
                      <span>{log.energy}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-lg mr-1">
                        {STRESS_EMOJIS[log.stress]}
                      </span>
                      <span>{log.stress}</span>
                    </TableCell>
                    <TableCell className="text-muted-foreground max-w-xs truncate">
                      {log.note || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
