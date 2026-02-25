import { WebPlugin } from "@capacitor/core";

import type {
  AppGuardPlugin,
  PermissionStatus,
  InstalledApp,
  AppUsageEntry,
  AppBreachEvent,
} from "./definitions";

/**
 * Web (非ネイティブ) 環境用 no-op 実装
 * ブラウザでは全機能が無効化され、安全なデフォルト値を返す。
 */
export class AppGuardWeb extends WebPlugin implements AppGuardPlugin {
  async checkPermissions(): Promise<PermissionStatus> {
    return { usageStats: false, overlay: false, accessibility: false };
  }

  async requestUsageStatsPermission(): Promise<{ granted: boolean }> {
    console.warn("[AppGuard] Web環境では使用統計パーミッションは利用不可です");
    return { granted: false };
  }

  async requestOverlayPermission(): Promise<{ granted: boolean }> {
    console.warn("[AppGuard] Web環境ではオーバーレイパーミッションは利用不可です");
    return { granted: false };
  }

  async openAccessibilitySettings(): Promise<void> {
    console.warn("[AppGuard] Web環境ではアクセシビリティ設定は利用不可です");
  }

  async getInstalledApps(): Promise<{ apps: InstalledApp[] }> {
    return { apps: [] };
  }

  async getUsageStats(_options: {
    startTime: number;
    endTime: number;
  }): Promise<{ entries: AppUsageEntry[] }> {
    return { entries: [] };
  }

  async startMonitoring(_options: {
    sessionId: number;
    blockedPackages: string[];
  }): Promise<void> {
    console.warn("[AppGuard] Web環境ではアプリ監視は利用不可です");
  }

  async stopMonitoring(): Promise<void> {
    // no-op
  }

  async getBreachLog(): Promise<{ breaches: AppBreachEvent[] }> {
    return { breaches: [] };
  }

  async enableHardBlock(_options: {
    sessionId: number;
    blockedPackages: string[];
    blockMessage: string;
    challengeMode: string;
  }): Promise<void> {
    console.warn("[AppGuard] Web環境ではハードブロックは利用不可です");
  }

  async disableHardBlock(): Promise<void> {
    // no-op
  }
}
