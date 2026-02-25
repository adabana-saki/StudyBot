"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import {
  getAppGuardSummary,
  getAppUsageHistory,
  getBreachHistory,
  AppGuardSummary,
  AppUsageLog,
  AppBreachEvent,
} from "@/lib/api";
import { isNative } from "@/lib/native";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import AppUsageChart from "@/components/AppUsageChart";
import AppDisciplineScore from "@/components/AppDisciplineScore";
import BreachTimeline from "@/components/BreachTimeline";
import PermissionSetupWizard from "@/components/PermissionSetupWizard";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BarChart3, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function AppUsagePage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<AppGuardSummary | null>(null);
  const [breaches, setBreaches] = useState<AppBreachEvent[]>([]);
  const [days, setDays] = useState("7");
  const [showPermissions, setShowPermissions] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [summaryData, breachData] = await Promise.all([
        getAppGuardSummary(parseInt(days)),
        getBreachHistory(10, 0),
      ]);
      setSummary(summaryData);
      setBreaches(breachData.items);
    } catch (err) {
      console.error("AppGuardデータ取得失敗:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) {
      loadData();
    }
  }, [authenticated, days]);

  if (!authenticated) return <LoadingSpinner />;

  return (
    <div className="container max-w-4xl mx-auto p-4 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/focus">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-1" />
            フォーカス
          </Button>
        </Link>
        <PageHeader
          title="アプリ使用時間"
          description="集中セッション中のアプリ使用状況を確認"
        />
      </div>

      {/* ネイティブ環境: パーミッション設定 */}
      {isNative() && (
        <div>
          {showPermissions ? (
            <PermissionSetupWizard
              requiredLevel="usage"
              onComplete={() => setShowPermissions(false)}
            />
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPermissions(true)}
            >
              パーミッション設定
            </Button>
          )}
        </div>
      )}

      {/* 期間選択 */}
      <div className="flex justify-end">
        <Select value={days} onValueChange={setDays}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">1日</SelectItem>
            <SelectItem value="7">7日</SelectItem>
            <SelectItem value="14">14日</SelectItem>
            <SelectItem value="30">30日</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : summary ? (
        <div className="space-y-6">
          {/* サマリーカード */}
          <AppDisciplineScore summary={summary} />

          {/* 使用時間チャート */}
          <AppUsageChart data={summary.top_apps} />

          {/* ブリーチタイムライン */}
          {breaches.length > 0 && <BreachTimeline breaches={breaches} />}
        </div>
      ) : (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            データがありません。ネイティブアプリからデータを同期してください。
          </CardContent>
        </Card>
      )}
    </div>
  );
}
