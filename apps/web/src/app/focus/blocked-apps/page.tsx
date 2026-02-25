"use client";

import { useEffect, useState } from "react";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import {
  getBlockedApps,
  addBlockedApp,
  BlockedApp,
} from "@/lib/api";
import { isNative, getInstalledApps } from "@/lib/native";
import type { InstalledApp } from "@/lib/native";
import LoadingSpinner from "@/components/LoadingSpinner";
import PageHeader from "@/components/PageHeader";
import BlockedAppList from "@/components/BlockedAppList";
import PermissionSetupWizard from "@/components/PermissionSetupWizard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Shield, Plus, ArrowLeft, Search } from "lucide-react";
import Link from "next/link";

export default function BlockedAppsPage() {
  const authenticated = useAuthGuard();
  const [loading, setLoading] = useState(true);
  const [blockedApps, setBlockedApps] = useState<BlockedApp[]>([]);
  const [installedApps, setInstalledApps] = useState<InstalledApp[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [showPermissions, setShowPermissions] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const blocked = await getBlockedApps();
      setBlockedApps(blocked);

      if (isNative()) {
        const apps = await getInstalledApps();
        setInstalledApps(apps);
      }
    } catch (err) {
      console.error("ブロックアプリ取得失敗:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated) {
      loadData();
    }
  }, [authenticated]);

  const handleAdd = async (app: InstalledApp) => {
    setAdding(true);
    try {
      await addBlockedApp(app.packageName, app.appName, app.category);
      await loadData();
    } catch (err) {
      console.error("ブロックアプリ追加失敗:", err);
    } finally {
      setAdding(false);
    }
  };

  const handleAddManual = async () => {
    if (!searchQuery.trim()) return;
    setAdding(true);
    try {
      await addBlockedApp(searchQuery.trim(), "", "custom");
      setSearchQuery("");
      await loadData();
    } catch (err) {
      console.error("ブロックアプリ追加失敗:", err);
    } finally {
      setAdding(false);
    }
  };

  if (!authenticated) return <LoadingSpinner />;

  // ブロック済みのパッケージ名セット
  const blockedSet = new Set(blockedApps.map((a) => a.package_name));

  // フィルタリング
  const filteredApps = installedApps.filter(
    (app) =>
      !blockedSet.has(app.packageName) &&
      (app.appName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.packageName.toLowerCase().includes(searchQuery.toLowerCase())),
  );

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
          title="ブロックアプリ管理"
          description="集中モード中にブロックするアプリを設定"
        />
      </div>

      {/* ネイティブパーミッション */}
      {isNative() && showPermissions && (
        <PermissionSetupWizard
          requiredLevel="usage"
          onComplete={() => setShowPermissions(false)}
        />
      )}

      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-6">
          {/* 登録済みブロックアプリ */}
          <BlockedAppList apps={blockedApps} onRemoved={loadData} />

          {/* アプリ追加セクション */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="w-5 h-5" />
                アプリを追加
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 手動追加 */}
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    placeholder="パッケージ名で検索 (例: com.twitter.android)"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Button
                  onClick={handleAddManual}
                  disabled={adding || !searchQuery.trim()}
                >
                  追加
                </Button>
              </div>

              {/* インストール済みアプリ一覧 (ネイティブのみ) */}
              {isNative() && filteredApps.length > 0 && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {filteredApps.slice(0, 20).map((app) => (
                    <div
                      key={app.packageName}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div>
                        <p className="font-medium text-sm">{app.appName}</p>
                        <p className="text-xs text-muted-foreground font-mono">
                          {app.packageName}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {app.category}
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleAdd(app)}
                          disabled={adding}
                        >
                          <Plus className="w-3 h-3 mr-1" />
                          ブロック
                        </Button>
                      </div>
                    </div>
                  ))}
                  {filteredApps.length > 20 && (
                    <p className="text-center text-sm text-muted-foreground py-2">
                      他 {filteredApps.length - 20} 件のアプリ（検索で絞り込み可能）
                    </p>
                  )}
                </div>
              )}

              {!isNative() && (
                <p className="text-sm text-muted-foreground text-center">
                  ネイティブアプリではインストール済みアプリから直接追加できます
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
