"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { BlockedApp } from "@/lib/api";
import { removeBlockedApp } from "@/lib/api";
import { Shield, Trash2 } from "lucide-react";

interface BlockedAppListProps {
  apps: BlockedApp[];
  onRemoved?: () => void;
}

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  social: { label: "SNS", color: "bg-pink-500/20 text-pink-400" },
  game: { label: "ゲーム", color: "bg-purple-500/20 text-purple-400" },
  video: { label: "動画", color: "bg-red-500/20 text-red-400" },
  news: { label: "ニュース", color: "bg-blue-500/20 text-blue-400" },
  custom: { label: "カスタム", color: "bg-gray-500/20 text-gray-400" },
};

export default function BlockedAppList({ apps, onRemoved }: BlockedAppListProps) {
  const [removing, setRemoving] = useState<string | null>(null);

  const handleRemove = async (packageName: string) => {
    setRemoving(packageName);
    try {
      await removeBlockedApp(packageName);
      onRemoved?.();
    } catch (err) {
      console.error("ブロックアプリ削除に失敗:", err);
    } finally {
      setRemoving(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5" />
          ブロックアプリ一覧
        </CardTitle>
      </CardHeader>
      <CardContent>
        {apps.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            ブロックアプリが登録されていません
          </p>
        ) : (
          <div className="space-y-2">
            {apps.map((app) => {
              const cat = CATEGORY_LABELS[app.category] || CATEGORY_LABELS.custom;
              return (
                <div
                  key={app.id}
                  className="flex items-center justify-between p-3 rounded-lg border"
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="font-medium text-sm">
                        {app.app_name || app.package_name}
                      </p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {app.package_name}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className={cat.color}>
                      {cat.label}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(app.package_name)}
                      disabled={removing === app.package_name}
                    >
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
