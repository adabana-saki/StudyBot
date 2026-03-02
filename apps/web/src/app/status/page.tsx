"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";
import {
  getSystemStatus,
  testPushNotification,
  type SystemStatus,
  type ComponentStatus,
} from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorBanner from "@/components/ErrorBanner";
import PageHeader from "@/components/PageHeader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Send, Database, Radio, Bot, Bell } from "lucide-react";

function statusColor(s: string) {
  if (s === "ok") return "text-green-500";
  if (s === "degraded") return "text-yellow-500";
  return "text-red-500";
}

function statusBg(s: string) {
  if (s === "ok") return "bg-green-500/10 border-green-500/30";
  if (s === "degraded") return "bg-yellow-500/10 border-yellow-500/30";
  return "bg-red-500/10 border-red-500/30";
}

function statusLabel(s: string) {
  if (s === "ok") return "正常";
  if (s === "degraded") return "一部異常";
  return "停止";
}

const COMPONENT_ICONS: Record<string, typeof Database> = {
  PostgreSQL: Database,
  Redis: Radio,
  "Discord Bot": Bot,
  Firebase: Bell,
};

function ComponentCard({ component }: { component: ComponentStatus }) {
  const Icon = COMPONENT_ICONS[component.name] || Database;
  return (
    <Card className={`border ${statusBg(component.status)}`}>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Icon className="h-4 w-4" />
            {component.name}
          </span>
          <span className={`text-sm font-semibold ${statusColor(component.status)}`}>
            {statusLabel(component.status)}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 text-sm text-muted-foreground">
        {component.latency_ms != null && (
          <p>レイテンシ: {component.latency_ms.toFixed(1)} ms</p>
        )}
        {component.details && (
          <>
            {component.details.bot_name && (
              <p>Bot: {String(component.details.bot_name)}</p>
            )}
            {component.details.guild_count != null && (
              <p>サーバー数: {String(component.details.guild_count)}</p>
            )}
            {component.details.ws_latency_ms != null && (
              <p>WS: {String(component.details.ws_latency_ms)} ms</p>
            )}
            {component.details.error && (
              <p className="text-red-400">{String(component.details.error)}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function StatusPage() {
  const router = useRouter();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pinging, setPinging] = useState(false);
  const [pingResult, setPingResult] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getSystemStatus();
      setStatus(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/auth/login");
      return;
    }
    fetchStatus();
  }, [router, fetchStatus]);

  const handlePing = async () => {
    setPinging(true);
    setPingResult(null);
    try {
      const res = await testPushNotification();
      setPingResult(res.message);
    } catch (e) {
      setPingResult(e instanceof Error ? e.message : "送信に失敗しました");
    } finally {
      setPinging(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBanner message={error} onDismiss={() => setError("")} />;
  if (!status) return null;

  const checkedAt = new Date(status.checked_at);
  const timeStr = checkedAt.toLocaleTimeString("ja-JP");

  return (
    <div className="container max-w-4xl mx-auto py-6 px-4">
      <PageHeader
        title="システム状態"
        description="各コンポーネントの接続状態を確認"
        action={
          <Button variant="outline" size="sm" onClick={fetchStatus} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            更新
          </Button>
        }
      />

      {/* Overall Status */}
      <Card className={`mb-6 border ${statusBg(status.status)}`}>
        <CardContent className="flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            <div className={`h-3 w-3 rounded-full ${status.status === "ok" ? "bg-green-500" : status.status === "degraded" ? "bg-yellow-500" : "bg-red-500"}`} />
            <div>
              <p className={`font-semibold ${statusColor(status.status)}`}>
                {statusLabel(status.status)}
              </p>
              <p className="text-xs text-muted-foreground">
                v{status.version} / 最終チェック: {timeStr}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Component Cards - 2x2 Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {status.components.map((comp) => (
          <ComponentCard key={comp.name} component={comp} />
        ))}
      </div>

      {/* Push Notification Test */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Send className="h-4 w-4" />
            プッシュ通知テスト
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            登録済みデバイスにテスト通知を送信します。
          </p>
          <div className="flex items-center gap-3">
            <Button onClick={handlePing} disabled={pinging} size="sm">
              {pinging ? "送信中..." : "テスト通知を送信"}
            </Button>
            {pingResult && (
              <span className="text-sm text-muted-foreground">{pingResult}</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
