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

