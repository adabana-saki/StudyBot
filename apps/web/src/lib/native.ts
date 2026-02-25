/**
 * Capacitor ネイティブ機能の統合モジュール
 * Web環境ではno-op、ネイティブ環境でのみ動作
 */
import { Capacitor } from "@capacitor/core";

// ネイティブ環境かどうかの判定
export const isNative = () => Capacitor.isNativePlatform();
export const isWeb = () => !isNative();

// ---------- プッシュ通知 ----------
// Firebase (google-services.json) 設定後に有効化
// npm install @capacitor/push-notifications してから initPushNotifications を実装

// ---------- ローカル通知 ----------

export async function scheduleLocalNotification(
  title: string,
  body: string,
  delaySeconds: number,
  data?: Record<string, unknown>,
) {
  if (!isNative()) {
    // Web: Notification API フォールバック
    if ("Notification" in window && Notification.permission === "granted") {
      setTimeout(() => new Notification(title, { body }), delaySeconds * 1000);
    }
    return;
  }

  const { LocalNotifications } = await import("@capacitor/local-notifications");

  await LocalNotifications.schedule({
    notifications: [
      {
        id: Date.now(),
        title,
        body,
        schedule: { at: new Date(Date.now() + delaySeconds * 1000) },
        extra: data,
      },
    ],
  });
}

// ---------- ネットワーク検知 ----------

export type NetworkStatus = {
  connected: boolean;
  connectionType: string;
};

export async function getNetworkStatus(): Promise<NetworkStatus> {
  if (!isNative()) {
    return { connected: navigator.onLine, connectionType: "unknown" };
  }

  const { Network } = await import("@capacitor/network");
  const status = await Network.getStatus();
  return {
    connected: status.connected,
    connectionType: status.connectionType,
  };
}

export async function onNetworkChange(
  callback: (status: NetworkStatus) => void,
) {
  if (!isNative()) {
    // Web: online/offline events
    const handler = () =>
      callback({ connected: navigator.onLine, connectionType: "unknown" });
    window.addEventListener("online", handler);
    window.addEventListener("offline", handler);
    return () => {
      window.removeEventListener("online", handler);
      window.removeEventListener("offline", handler);
    };
  }

  const { Network } = await import("@capacitor/network");
  const handle = await Network.addListener("networkStatusChange", (status) => {
    callback({
      connected: status.connected,
      connectionType: status.connectionType,
    });
  });
  return () => handle.remove();
}

// ---------- ディープリンク ----------

export async function setupDeepLinks(
  onDeepLink: (url: string) => void,
) {
  if (!isNative()) return;

  const { App } = await import("@capacitor/app");

  // アプリがディープリンクで開かれた時
  App.addListener("appUrlOpen", (event) => {
    console.log("[DeepLink] URL:", event.url);
    // studybot://dashboard → /dashboard
    // https://studybot.example.com/dashboard → /dashboard
    const url = new URL(event.url);
    const path = url.pathname || url.host;
    onDeepLink(path);
  });
}

// ---------- ステータスバー ----------

export async function configureStatusBar() {
  if (!isNative()) return;

  const { StatusBar, Style } = await import("@capacitor/status-bar");

  await StatusBar.setStyle({ style: Style.Dark });
  await StatusBar.setBackgroundColor({ color: "#0f1729" });
  await StatusBar.setOverlaysWebView({ overlay: false });
}

// ---------- スプラッシュスクリーン ----------

export async function hideSplashScreen() {
  if (!isNative()) return;

  const { SplashScreen } = await import("@capacitor/splash-screen");
  await SplashScreen.hide();
}

// ---------- AppGuard ----------

import type {
  PermissionStatus,
  InstalledApp,
  AppUsageEntry,
  AppBreachEvent,
} from "@/plugins/app-guard/definitions";

export type { PermissionStatus, InstalledApp, AppUsageEntry, AppBreachEvent };

export async function getAppGuardPermissions(): Promise<PermissionStatus> {
  if (!isNative()) {
    return { usageStats: false, overlay: false, accessibility: false };
  }
  const { AppGuard } = await import("@/plugins/app-guard");
  return AppGuard.checkPermissions();
}

export async function requestUsageStatsPermission(): Promise<boolean> {
  if (!isNative()) return false;
  const { AppGuard } = await import("@/plugins/app-guard");
  const result = await AppGuard.requestUsageStatsPermission();
  return result.granted;
}

export async function requestOverlayPermission(): Promise<boolean> {
  if (!isNative()) return false;
  const { AppGuard } = await import("@/plugins/app-guard");
  const result = await AppGuard.requestOverlayPermission();
  return result.granted;
}

export async function openAccessibilitySettings(): Promise<void> {
  if (!isNative()) return;
  const { AppGuard } = await import("@/plugins/app-guard");
  await AppGuard.openAccessibilitySettings();
}

export async function getInstalledApps(): Promise<InstalledApp[]> {
  if (!isNative()) return [];
  const { AppGuard } = await import("@/plugins/app-guard");
  const result = await AppGuard.getInstalledApps();
  return result.apps;
}

export async function getNativeUsageStats(
  startTime: number,
  endTime: number,
): Promise<AppUsageEntry[]> {
  if (!isNative()) return [];
  const { AppGuard } = await import("@/plugins/app-guard");
  const result = await AppGuard.getUsageStats({ startTime, endTime });
  return result.entries;
}

export async function startAppMonitoring(
  sessionId: number,
  blockedPackages: string[],
): Promise<void> {
  if (!isNative()) return;
  const { AppGuard } = await import("@/plugins/app-guard");
  await AppGuard.startMonitoring({ sessionId, blockedPackages });
}

export async function stopAppMonitoring(): Promise<AppBreachEvent[]> {
  if (!isNative()) return [];
  const { AppGuard } = await import("@/plugins/app-guard");
  const result = await AppGuard.getBreachLog();
  await AppGuard.stopMonitoring();
  return result.breaches;
}

export async function enableHardBlock(
  sessionId: number,
  blockedPackages: string[],
  blockMessage: string,
  challengeMode: string,
): Promise<void> {
  if (!isNative()) return;
  const { AppGuard } = await import("@/plugins/app-guard");
  await AppGuard.enableHardBlock({
    sessionId,
    blockedPackages,
    blockMessage,
    challengeMode,
  });
}

export async function disableHardBlock(): Promise<void> {
  if (!isNative()) return;
  const { AppGuard } = await import("@/plugins/app-guard");
  await AppGuard.disableHardBlock();
}

