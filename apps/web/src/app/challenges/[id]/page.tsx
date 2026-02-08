"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import {
  getChallengeDetail,
  joinChallenge,
  challengeCheckin,
  ChallengeDetail,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Users,
  Calendar,
  Target,
  Trophy,
  UserPlus,
  CheckCircle,
} from "lucide-react";

function daysRemaining(endDate: string): number {
  const end = new Date(endDate);
  const now = new Date();
  const diff = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

const GOAL_TYPE_LABELS: Record<string, string> = {
  study_minutes: "学習時間（分）",
  session_count: "セッション数",
  tasks_completed: "タスク完了数",
};

export default function ChallengeDetailPage() {
  const authenticated = useAuthGuard();
  const params = useParams();
  const challengeId = Number(params.id);

  const [loading, setLoading] = useState(true);
  const [challenge, setChallenge] = useState<ChallengeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [checkinProgress, setCheckinProgress] = useState("0");
  const [checkinNote, setCheckinNote] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const data = await getChallengeDetail(challengeId);
      setChallenge(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "データの取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  }, [challengeId]);

  useEffect(() => {
    if (authenticated && challengeId) fetchData();
  }, [authenticated, challengeId, fetchData]);

  const handleJoin = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await joinChallenge(challengeId);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "参加に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleCheckin = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await challengeCheckin(
        challengeId,
        parseInt(checkinProgress) || 0,
        checkinNote
      );
      setCheckinProgress("0");
      setCheckinNote("");
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "チェックインに失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  if (!authenticated || loading) return <LoadingSpinner />;
  if (!challenge) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-muted-foreground">
        チャレンジが見つかりません
      </div>
    );
  }

  const remaining = daysRemaining(challenge.end_date);
  const medals = ["🥇", "🥈", "🥉"];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader title={challenge.name} description={challenge.description} />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            閉じる
          </button>
        </div>
      )}

      {/* Challenge Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4 text-center">
            <Target className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <div className="text-2xl font-bold">{challenge.goal_target}</div>
            <div className="text-xs text-muted-foreground">
              {GOAL_TYPE_LABELS[challenge.goal_type] || challenge.goal_type}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Users className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <div className="text-2xl font-bold">
              {challenge.participant_count}
            </div>
            <div className="text-xs text-muted-foreground">参加者</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Calendar className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <div className="text-2xl font-bold">{remaining}</div>
            <div className="text-xs text-muted-foreground">残り日数</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <Trophy className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <div className="text-2xl font-bold">{challenge.xp_multiplier}x</div>
            <div className="text-xs text-muted-foreground">XPボーナス</div>
          </CardContent>
        </Card>
      </div>

      {/* Actions */}
      {challenge.status === "active" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Join */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <UserPlus className="h-4 w-4" />
                チャレンジに参加
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                onClick={handleJoin}
                disabled={actionLoading}
                className="w-full"
              >
                参加する
              </Button>
            </CardContent>
          </Card>

          {/* Checkin */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                チェックイン
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>進捗値</Label>
                <Input
                  type="number"
                  min={0}
                  value={checkinProgress}
                  onChange={(e) => setCheckinProgress(e.target.value)}
                  placeholder="0"
                />
              </div>
              <div>
                <Label>メモ（任意）</Label>
                <Input
                  value={checkinNote}
                  onChange={(e) => setCheckinNote(e.target.value)}
                  placeholder="今日の学習内容..."
                />
              </div>
              <Button
                onClick={handleCheckin}
                disabled={actionLoading}
                className="w-full"
                variant="secondary"
              >
                チェックイン
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Leaderboard */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5" />
            リーダーボード
          </CardTitle>
        </CardHeader>
        <CardContent>
          {challenge.participants.length === 0 ? (
            <p className="text-muted-foreground text-sm text-center py-8">
              まだ参加者がいません
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">順位</TableHead>
                    <TableHead>ユーザー</TableHead>
                    <TableHead>進捗</TableHead>
                    <TableHead>チェックイン</TableHead>
                    <TableHead>状態</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {challenge.participants.map((p, i) => {
                    const pct =
                      challenge.goal_target > 0
                        ? Math.min(
                            100,
                            Math.round(
                              (p.progress / challenge.goal_target) * 100
                            )
                          )
                        : 0;
                    return (
                      <TableRow key={p.user_id}>
                        <TableCell className="font-medium">
                          {i < 3 ? medals[i] : `#${i + 1}`}
                        </TableCell>
                        <TableCell>{p.username}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full transition-all"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-sm text-muted-foreground">
                              {p.progress}/{challenge.goal_target} ({pct}%)
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>{p.checkins}回</TableCell>
                        <TableCell>
                          {p.completed ? (
                            <Badge variant="default">達成</Badge>
                          ) : (
                            <Badge variant="outline">進行中</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Challenge Info */}
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">チャレンジ情報</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <p>作成者: {challenge.creator_name}</p>
          <p>
            期間: {challenge.start_date} ~ {challenge.end_date} (
            {challenge.duration_days}日間)
          </p>
          <p>ステータス: {challenge.status}</p>
          <p>
            作成日:{" "}
            {new Date(challenge.created_at).toLocaleDateString("ja-JP")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
