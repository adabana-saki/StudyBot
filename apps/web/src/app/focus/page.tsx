"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import {
  getFocusStatus,
  startFocus,
  endFocus,
  unlockWithCode,
  penaltyUnlock,
  requestFocusCode,
  getLockSettings,
  updateLockSettings,
  getFocusHistory,
  FocusSession,
  FocusHistoryEntry,
  LockSettings,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import BlockOverlay from "@/components/BlockOverlay";
import ChallengeModal from "@/components/ChallengeModal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Focus,
  Play,
  Settings,
  Clock,
  Coins,
  Lock,
  Unlock,
  AlertTriangle,
  Send,
  History,
} from "lucide-react";

const UNLOCK_LEVEL_INFO: Record<
  number,
  { name: string; description: string }
> = {
  1: { name: "タイマー完了", description: "タイマー満了で自動解除" },
  2: {
    name: "確認コード",
    description: "開始時にDMで6桁コードを受け取り入力して解除",
  },
  3: {
    name: "DMコード",
    description: "リクエスト後にDMで8文字コードを受け取り入力して解除",
  },
  4: {
    name: "学習完了コード",
    description: "学習セッション完了後にDMで12文字コードを受け取り入力して解除",
  },
  5: {
    name: "ペナルティ解除",
    description: "全ベット+残高20%没収で即時解除",
  },
};

const DURATION_OPTIONS = [15, 25, 30, 45, 60, 90, 120];

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function CircularTimer({
  remaining,
  total,
}: {
  remaining: number;
  total: number;
}) {
  const progress = total > 0 ? (total - remaining) / total : 0;
  const radius = 90;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - progress);

  return (
    <div className="relative w-56 h-56 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 200 200">
        {/* Background circle */}
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth="8"
        />
        {/* Progress circle */}
        <circle
          cx="100"
          cy="100"
          r={radius}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-1000"
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold font-mono">
          {formatTime(remaining)}
        </span>
        <span className="text-sm text-muted-foreground mt-1">残り時間</span>
      </div>
    </div>
  );
}

export default function FocusPage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<FocusSession | null>(null);
  const [history, setHistory] = useState<FocusHistoryEntry[]>([]);
  const [settings, setSettings] = useState<LockSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [penaltyDialogOpen, setPenaltyDialogOpen] = useState(false);
  const [codeRequestSent, setCodeRequestSent] = useState(false);

  // Challenge state
  const [challengeModalOpen, setChallengeModalOpen] = useState(false);
  const [dismissedUntil, setDismissedUntil] = useState<Date | null>(null);

  // Start form state
  const [startDuration, setStartDuration] = useState("60");
  const [startLevel, setStartLevel] = useState("1");
  const [startBet, setStartBet] = useState("0");
  const [startChallengeMode, setStartChallengeMode] = useState("none");

  // Unlock code input
  const [unlockCode, setUnlockCode] = useState("");

  // Settings form
  const [settingsForm, setSettingsForm] = useState<LockSettings>({
    default_unlock_level: 1,
    default_duration: 60,
    default_coin_bet: 0,
    block_categories: [],
    custom_blocked_urls: [],
    challenge_mode: "none",
    challenge_difficulty: 1,
    block_message: "",
  });

  // Timer
  const [remaining, setRemaining] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const syncRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [sessionData, historyData, settingsData] = await Promise.all([
        getFocusStatus(),
        getFocusHistory(),
        getLockSettings(),
      ]);
      setSession(sessionData);
      setHistory(historyData);
      setSettings(settingsData);
      if (settingsData) {
        setSettingsForm(settingsData);
        setStartDuration(String(settingsData.default_duration));
        setStartLevel(String(settingsData.default_unlock_level));
        setStartBet(String(settingsData.default_coin_bet));
        setStartChallengeMode(settingsData.challenge_mode || "none");
      }
      if (sessionData) {
        setRemaining(sessionData.remaining_seconds);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "データの取得に失敗しました"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authenticated) fetchData();
  }, [authenticated, fetchData]);

  // 1-second countdown timer
  useEffect(() => {
    if (session && remaining > 0) {
      timerRef.current = setInterval(() => {
        setRemaining((prev) => Math.max(0, prev - 1));
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [session, remaining > 0]);

  // 30-second server sync
  useEffect(() => {
    if (session) {
      syncRef.current = setInterval(async () => {
        try {
          const fresh = await getFocusStatus();
          if (fresh) {
            setSession(fresh);
            setRemaining(fresh.remaining_seconds);
          } else {
            setSession(null);
            setRemaining(0);
            fetchData();
          }
        } catch {
          // ignore sync errors
        }
      }, 30000);
    }
    return () => {
      if (syncRef.current) clearInterval(syncRef.current);
    };
  }, [session, fetchData]);

  const handleStart = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const result = await startFocus({
        duration: parseInt(startDuration),
        unlock_level: parseInt(startLevel),
        coins_bet: parseInt(startBet) || 0,
        challenge_mode: startChallengeMode,
      });
      setSession(result);
      setRemaining(result.remaining_seconds);
      setCodeRequestSent(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "セッション開始に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleEnd = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await endFocus();
      setSession(null);
      setRemaining(0);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "セッション終了に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnlockCode = async () => {
    if (!unlockCode.trim()) return;
    setActionLoading(true);
    setError(null);
    try {
      await unlockWithCode(unlockCode.trim());
      setSession(null);
      setRemaining(0);
      setUnlockCode("");
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "コード検証に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handlePenaltyUnlock = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await penaltyUnlock();
      setSession(null);
      setRemaining(0);
      setPenaltyDialogOpen(false);
      await fetchData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "ペナルティ解除に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestCode = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await requestFocusCode();
      setCodeRequestSent(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "コードリクエストに失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const updated = await updateLockSettings(settingsForm);
      setSettings(updated);
      setSettingsOpen(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "設定保存に失敗しました"
      );
    } finally {
      setActionLoading(false);
    }
  };

  if (!authenticated || loading) return <LoadingSpinner />;

  const totalSeconds = session ? session.duration_minutes * 60 : 0;
  const unlockLevel = session?.unlock_level ?? 1;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        title="フォーカスモード"
        description="集中して学習に取り組もう"
        action={
          <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4 mr-2" />
                設定
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>フォーカス設定</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                <div>
                  <Label>デフォルトアンロックレベル</Label>
                  <Select
                    value={String(settingsForm.default_unlock_level)}
                    onValueChange={(v) =>
                      setSettingsForm({
                        ...settingsForm,
                        default_unlock_level: parseInt(v),
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[1, 2, 3, 4, 5].map((lv) => (
                        <SelectItem key={lv} value={String(lv)}>
                          Lv{lv}: {UNLOCK_LEVEL_INFO[lv].name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>デフォルト時間（分）</Label>
                  <Select
                    value={String(settingsForm.default_duration)}
                    onValueChange={(v) =>
                      setSettingsForm({
                        ...settingsForm,
                        default_duration: parseInt(v),
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {DURATION_OPTIONS.map((d) => (
                        <SelectItem key={d} value={String(d)}>
                          {d}分
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>デフォルトベットコイン</Label>
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    value={settingsForm.default_coin_bet}
                    onChange={(e) =>
                      setSettingsForm({
                        ...settingsForm,
                        default_coin_bet: parseInt(e.target.value) || 0,
                      })
                    }
                  />
                </div>
                <div>
                  <Label>ブロックカテゴリ</Label>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {["sns", "games", "entertainment", "news"].map((cat) => {
                      const labels: Record<string, string> = {
                        sns: "SNS",
                        games: "ゲーム",
                        entertainment: "エンタメ",
                        news: "ニュース",
                      };
                      const checked =
                        settingsForm.block_categories.includes(cat);
                      return (
                        <label
                          key={cat}
                          className="flex items-center gap-2 text-sm"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => {
                              const cats = checked
                                ? settingsForm.block_categories.filter(
                                    (c) => c !== cat
                                  )
                                : [...settingsForm.block_categories, cat];
                              setSettingsForm({
                                ...settingsForm,
                                block_categories: cats,
                              });
                            }}
                            className="rounded"
                          />
                          {labels[cat]}
                        </label>
                      );
                    })}
                  </div>
                </div>
                <div>
                  <Label>チャレンジモード</Label>
                  <Select
                    value={settingsForm.challenge_mode || "none"}
                    onValueChange={(v) =>
                      setSettingsForm({
                        ...settingsForm,
                        challenge_mode: v,
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">なし</SelectItem>
                      <SelectItem value="math">計算チャレンジ</SelectItem>
                      <SelectItem value="typing">タイピングチャレンジ</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>チャレンジ難易度</Label>
                  <Select
                    value={String(settingsForm.challenge_difficulty || 1)}
                    onValueChange={(v) =>
                      setSettingsForm({
                        ...settingsForm,
                        challenge_difficulty: parseInt(v),
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[1, 2, 3, 4, 5].map((d) => (
                        <SelectItem key={d} value={String(d)}>
                          Lv{d}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>カスタムブロックメッセージ</Label>
                  <Input
                    value={settingsForm.block_message || ""}
                    onChange={(e) =>
                      setSettingsForm({
                        ...settingsForm,
                        block_message: e.target.value,
                      })
                    }
                    placeholder="集中して頑張りましょう！"
                    maxLength={200}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    空欄の場合はランダムメッセージが表示されます
                  </p>
                </div>
                <Button
                  onClick={handleSaveSettings}
                  disabled={actionLoading}
                  className="w-full"
                >
                  保存
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        }
      />

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 mb-4 text-destructive text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 underline"
          >
            閉じる
          </button>
        </div>
      )}

      {/* Block Overlay */}
      {session && session.challenge_mode !== "none" && (
        <BlockOverlay
          remaining={remaining}
          totalSeconds={totalSeconds}
          blockCategories={session.block_categories || []}
          blockMessage={session.block_message || ""}
          challengeMode={session.challenge_mode}
          onChallengeRequest={() => setChallengeModalOpen(true)}
          dismissedUntil={dismissedUntil}
        />
      )}

      {/* Challenge Modal */}
      {session && (
        <ChallengeModal
          open={challengeModalOpen}
          onClose={() => setChallengeModalOpen(false)}
          challengeMode={session.challenge_mode || "none"}
          difficulty={settings?.challenge_difficulty || 1}
          onSuccess={(until) => {
            setDismissedUntil(until);
            setChallengeModalOpen(false);
          }}
        />
      )}

      {/* Active Session Panel */}
      {session ? (
        <Card className="mb-8">
          <CardContent className="p-8">
            <div className="text-center mb-6">
              <div className="flex items-center justify-center gap-2 mb-4">
                <Lock className="h-5 w-5 text-primary" />
                <Badge variant="default">
                  Lv{unlockLevel}: {UNLOCK_LEVEL_INFO[unlockLevel]?.name}
                </Badge>
                {session.coins_bet > 0 && (
                  <Badge variant="secondary">
                    <Coins className="h-3 w-3 mr-1" />
                    {session.coins_bet} コイン
                  </Badge>
                )}
              </div>

              <CircularTimer remaining={remaining} total={totalSeconds} />
            </div>

            {/* Unlock Area */}
            <div className="mt-6 space-y-4">
              {unlockLevel === 1 && (
                <div className="text-center">
                  {remaining <= 0 ? (
                    <Button onClick={handleEnd} disabled={actionLoading}>
                      <Unlock className="h-4 w-4 mr-2" />
                      セッション完了
                    </Button>
                  ) : (
                    <p className="text-muted-foreground text-sm">
                      <Clock className="h-4 w-4 inline mr-1" />
                      タイマー完了まで待ちましょう
                    </p>
                  )}
                </div>
              )}

              {unlockLevel === 2 && (
                <div className="max-w-xs mx-auto space-y-2">
                  <Label>6桁確認コードを入力</Label>
                  <div className="flex gap-2">
                    <Input
                      value={unlockCode}
                      onChange={(e) => setUnlockCode(e.target.value)}
                      placeholder="123456"
                      maxLength={6}
                      className="font-mono text-center text-lg tracking-widest"
                    />
                    <Button
                      onClick={handleUnlockCode}
                      disabled={actionLoading || unlockCode.length < 6}
                    >
                      <Send className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    開始時にDMで送信されたコードを入力してください
                  </p>
                </div>
              )}

              {unlockLevel === 3 && (
                <div className="max-w-xs mx-auto space-y-3">
                  {!codeRequestSent ? (
                    <Button
                      onClick={handleRequestCode}
                      disabled={actionLoading}
                      variant="outline"
                      className="w-full"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      コードを取得
                    </Button>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center">
                      DiscordのDMにコードを送信しました
                    </p>
                  )}
                  <div>
                    <Label>8文字コードを入力</Label>
                    <div className="flex gap-2 mt-1">
                      <Input
                        value={unlockCode}
                        onChange={(e) =>
                          setUnlockCode(e.target.value.toUpperCase())
                        }
                        placeholder="ABC12345"
                        maxLength={8}
                        className="font-mono text-center text-lg tracking-widest"
                      />
                      <Button
                        onClick={handleUnlockCode}
                        disabled={actionLoading || unlockCode.length < 8}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {unlockLevel === 4 && (
                <div className="max-w-sm mx-auto space-y-3 text-center">
                  <p className="text-sm text-muted-foreground">
                    学習セッションを完了するとDiscord DMにコードが届きます。
                    <br />
                    <code className="text-primary">/study log</code> または{" "}
                    <code className="text-primary">/pomodoro</code>{" "}
                    で学習を完了してください。
                  </p>
                  {!codeRequestSent && (
                    <Button
                      onClick={handleRequestCode}
                      disabled={actionLoading}
                      variant="outline"
                      size="sm"
                    >
                      <Send className="h-4 w-4 mr-2" />
                      コードリクエスト
                    </Button>
                  )}
                  <div>
                    <Label>12文字コードを入力</Label>
                    <div className="flex gap-2 mt-1">
                      <Input
                        value={unlockCode}
                        onChange={(e) =>
                          setUnlockCode(e.target.value.toUpperCase())
                        }
                        placeholder="ABCD12345678"
                        maxLength={12}
                        className="font-mono text-center tracking-widest"
                      />
                      <Button
                        onClick={handleUnlockCode}
                        disabled={actionLoading || unlockCode.length < 12}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              )}

              {unlockLevel === 5 && (
                <div className="text-center space-y-3">
                  <p className="text-sm text-muted-foreground">
                    ペナルティを支払ってロックを解除できます。
                  </p>
                  <Dialog
                    open={penaltyDialogOpen}
                    onOpenChange={setPenaltyDialogOpen}
                  >
                    <DialogTrigger asChild>
                      <Button variant="destructive">
                        <AlertTriangle className="h-4 w-4 mr-2" />
                        ペナルティ解除
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-sm">
                      <DialogHeader>
                        <DialogTitle>ペナルティ解除の確認</DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 mt-4">
                        <p className="text-sm text-muted-foreground">
                          以下のコインを失います:
                        </p>
                        <ul className="text-sm space-y-1">
                          <li>
                            ベットコイン:{" "}
                            <span className="font-bold">
                              {session.coins_bet}枚
                            </span>
                          </li>
                          <li>
                            残高の20%:{" "}
                            <span className="font-bold text-destructive">
                              没収
                            </span>
                          </li>
                        </ul>
                        <div className="flex gap-2">
                          <Button
                            variant="destructive"
                            onClick={handlePenaltyUnlock}
                            disabled={actionLoading}
                            className="flex-1"
                          >
                            解除する
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => setPenaltyDialogOpen(false)}
                            className="flex-1"
                          >
                            キャンセル
                          </Button>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        /* Session Start Panel */
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Focus className="h-5 w-5" />
              セッション開始
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <Label>時間</Label>
                <Select value={startDuration} onValueChange={setStartDuration}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DURATION_OPTIONS.map((d) => (
                      <SelectItem key={d} value={String(d)}>
                        {d}分
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>アンロックレベル</Label>
                <Select value={startLevel} onValueChange={setStartLevel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 4, 5].map((lv) => (
                      <SelectItem key={lv} value={String(lv)}>
                        Lv{lv}: {UNLOCK_LEVEL_INFO[lv].name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  {UNLOCK_LEVEL_INFO[parseInt(startLevel)]?.description}
                </p>
              </div>
              <div>
                <Label>コインベット</Label>
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={startBet}
                  onChange={(e) => setStartBet(e.target.value)}
                  disabled={parseInt(startLevel) < 2}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  0〜100（Lv2以上）
                </p>
              </div>
              <div>
                <Label>チャレンジモード</Label>
                <Select value={startChallengeMode} onValueChange={setStartChallengeMode}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">なし</SelectItem>
                    <SelectItem value="math">計算チャレンジ</SelectItem>
                    <SelectItem value="typing">タイピングチャレンジ</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground mt-1">
                  解除時にチャレンジが必要
                </p>
              </div>
            </div>

            <Button
              onClick={handleStart}
              disabled={actionLoading}
              className="w-full sm:w-auto"
              size="lg"
            >
              <Play className="h-4 w-4 mr-2" />
              フォーカス開始
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Session History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            セッション履歴
          </CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-muted-foreground text-sm text-center py-8">
              まだセッション履歴がありません
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>日時</TableHead>
                    <TableHead>時間</TableHead>
                    <TableHead>レベル</TableHead>
                    <TableHead>ベット</TableHead>
                    <TableHead>結果</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="text-sm">
                        {new Date(entry.started_at).toLocaleDateString("ja-JP", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell>{entry.duration_minutes}分</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          Lv{entry.unlock_level}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {entry.coins_bet > 0 ? `${entry.coins_bet}枚` : "-"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            entry.state === "completed"
                              ? "default"
                              : entry.state === "active"
                                ? "secondary"
                                : "destructive"
                          }
                        >
                          {entry.state === "completed"
                            ? "完了"
                            : entry.state === "active"
                              ? "進行中"
                              : "中断"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
