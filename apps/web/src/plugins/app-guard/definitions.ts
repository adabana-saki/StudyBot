/**
 * AppGuard Capacitor Plugin — インターフェース定義
 *
 * Android ネイティブAPIを利用したアプリ使用時間トラッキング &
 * フォーカスモード時のアプリブロック機能を提供する。
 */

import type { PluginListenerHandle } from "@capacitor/core";

// ---------- 共通型 ----------

export interface PermissionStatus {
  usageStats: boolean;
  overlay: boolean;
  accessibility: boolean;
}

export interface InstalledApp {
  packageName: string;
  appName: string;
  category: string;
}

export interface AppUsageEntry {
  packageName: string;
  appName: string;
  foregroundTimeMs: number;
  periodStart: number; // epoch ms
  periodEnd: number;
}

export interface AppBreachEvent {
  packageName: string;
  appName: string;
  breachDurationMs: number;
  occurredAt: number; // epoch ms
}

// ---------- プラグインインターフェース ----------

export interface AppGuardPlugin {
  // パーミッション管理
  checkPermissions(): Promise<PermissionStatus>;
  requestUsageStatsPermission(): Promise<{ granted: boolean }>;
  requestOverlayPermission(): Promise<{ granted: boolean }>;
  openAccessibilitySettings(): Promise<void>;

  // Phase A: 使用時間トラッキング
  getInstalledApps(): Promise<{ apps: InstalledApp[] }>;
  getUsageStats(options: {
    startTime: number;
    endTime: number;
  }): Promise<{ entries: AppUsageEntry[] }>;

  // Phase B: ソフトブロック（監視モード）
  startMonitoring(options: {
    sessionId: number;
    blockedPackages: string[];
  }): Promise<void>;
  stopMonitoring(): Promise<void>;
  getBreachLog(): Promise<{ breaches: AppBreachEvent[] }>;

  // Phase C: ハードブロック（オーバーレイ）
  enableHardBlock(options: {
    sessionId: number;
    blockedPackages: string[];
    blockMessage: string;
    challengeMode: string;
  }): Promise<void>;
  disableHardBlock(): Promise<void>;

  // リスナー
  addListener(
    eventName: "appBreach",
    handler: (event: AppBreachEvent) => void,
  ): Promise<PluginListenerHandle>;
}
