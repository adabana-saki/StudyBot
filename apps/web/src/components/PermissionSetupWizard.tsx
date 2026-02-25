"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  isNative,
  getAppGuardPermissions,
  requestUsageStatsPermission,
  requestOverlayPermission,
  openAccessibilitySettings,
} from "@/lib/native";
import type { PermissionStatus } from "@/lib/native";
import { CheckCircle, Circle, Shield, BarChart3, Layers } from "lucide-react";

interface PermissionSetupWizardProps {
  onComplete?: () => void;
  requiredLevel?: "usage" | "soft" | "hard";
}

const STEPS = [
  {
    key: "usageStats" as const,
    title: "使用統計アクセス",
    description: "アプリの使用時間データを取得します",
    icon: BarChart3,
    level: "usage" as const,
  },
  {
    key: "overlay" as const,
    title: "オーバーレイ表示",
    description: "禁止アプリ使用時にブロック画面を表示します",
    icon: Layers,
    level: "hard" as const,
  },
  {
    key: "accessibility" as const,
    title: "アクセシビリティ",
    description: "アプリの切り替えをリアルタイムに検知します",
    icon: Shield,
    level: "hard" as const,
  },
];

export default function PermissionSetupWizard({
  onComplete,
  requiredLevel = "usage",
}: PermissionSetupWizardProps) {
  const [permissions, setPermissions] = useState<PermissionStatus>({
    usageStats: false,
    overlay: false,
    accessibility: false,
  });
  const [loading, setLoading] = useState(false);

  const refreshPermissions = async () => {
    const perms = await getAppGuardPermissions();
    setPermissions(perms);
  };

  useEffect(() => {
    if (isNative()) {
      refreshPermissions();
    }
  }, []);

  // 必要なステップのみ表示
  const visibleSteps = STEPS.filter((step) => {
    if (requiredLevel === "usage") return step.level === "usage";
    if (requiredLevel === "soft") return step.level === "usage";
    return true; // hard: 全て表示
  });

  const allGranted = visibleSteps.every((step) => permissions[step.key]);

  useEffect(() => {
    if (allGranted && onComplete) {
      onComplete();
    }
  }, [allGranted, onComplete]);

  const handleRequest = async (key: string) => {
    setLoading(true);
    try {
      if (key === "usageStats") {
        await requestUsageStatsPermission();
      } else if (key === "overlay") {
        await requestOverlayPermission();
      } else if (key === "accessibility") {
        await openAccessibilitySettings();
      }
      // 設定画面から戻ってきた後にリフレッシュ
      setTimeout(refreshPermissions, 1000);
    } finally {
      setLoading(false);
    }
  };

  if (!isNative()) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          <p>AppGuard はネイティブアプリでのみ利用可能です</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5" />
          AppGuard パーミッション設定
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {visibleSteps.map((step) => {
          const granted = permissions[step.key];
          const Icon = step.icon;
          return (
            <div
              key={step.key}
              className="flex items-center justify-between p-4 rounded-lg border"
            >
              <div className="flex items-center gap-3">
                {granted ? (
                  <CheckCircle className="w-5 h-5 text-green-500" />
                ) : (
                  <Circle className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4" />
                    <span className="font-medium">{step.title}</span>
                    {granted && (
                      <Badge variant="secondary" className="text-xs">
                        許可済み
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              </div>
              {!granted && (
                <Button
                  size="sm"
                  onClick={() => handleRequest(step.key)}
                  disabled={loading}
                >
                  設定を開く
                </Button>
              )}
            </div>
          );
        })}
        {allGranted && (
          <div className="text-center py-2 text-green-500 font-medium">
            全てのパーミッションが許可されています
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={refreshPermissions}
          className="w-full"
        >
          パーミッション状態を再確認
        </Button>
      </CardContent>
    </Card>
  );
}
