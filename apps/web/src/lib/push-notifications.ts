/**
 * FCMプッシュ通知クライアント
 * Capacitor PushNotifications プラグインを使用してFCMトークン登録・通知処理を行う
 */

import { Capacitor } from "@capacitor/core";
import type { ActionPerformed, PushNotificationSchema, Token } from "@capacitor/push-notifications";

/**
 * プッシュ通知を初期化しFCMトークンをAPIに登録する
 */
export async function initPushNotifications(
  apiBaseUrl: string,
  authToken: string,
): Promise<void> {
  if (!Capacitor.isNativePlatform()) {
    console.log("[Push] Web環境のためスキップ");
    return;
  }

  const { PushNotifications } = await import("@capacitor/push-notifications");

  // 権限リクエスト
  const permResult = await PushNotifications.requestPermissions();
  if (permResult.receive !== "granted") {
    console.warn("[Push] 通知権限が拒否されました");
    return;
  }

  // FCMトークン取得時 → APIに登録
  await PushNotifications.addListener("registration", async (token: Token) => {
    console.log("[Push] FCMトークン取得:", token.value.substring(0, 20) + "...");
    try {
      const platform = Capacitor.getPlatform(); // "android" | "ios"
      await fetch(`${apiBaseUrl}/api/notifications/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          device_token: token.value,
          platform,
        }),
      });
      console.log("[Push] トークン登録完了");
    } catch (err) {
      console.error("[Push] トークン登録失敗:", err);
    }
  });

  // トークン取得エラー
  await PushNotifications.addListener("registrationError", (err) => {
    console.error("[Push] 登録エラー:", err);
  });

  // フォアグラウンドで通知受信時
  await PushNotifications.addListener(
    "pushNotificationReceived",
    (notification: PushNotificationSchema) => {
      console.log("[Push] フォアグラウンド通知:", notification.title);
      // ブラウザのNotification APIでフォアグラウンド表示
      if ("Notification" in window && Notification.permission === "granted") {
        new Notification(notification.title || "StudyBot", {
          body: notification.body || "",
        });
      }
    },
  );

  // 通知タップ時 → ディープリンクルーティング
  await PushNotifications.addListener(
    "pushNotificationActionPerformed",
    (action: ActionPerformed) => {
      console.log("[Push] 通知アクション:", action.notification.data);
      const data = action.notification.data;
      if (data?.deepLink && typeof window !== "undefined") {
        window.location.href = data.deepLink;
      }
    },
  );

  // FCMに登録開始
  await PushNotifications.register();
  console.log("[Push] FCM登録開始");
}

/**
 * プッシュ通知を解除しトークンをAPIから無効化する
 */
export async function unregisterPushNotifications(
  apiBaseUrl: string,
  authToken: string,
  deviceToken?: string,
): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;

  if (deviceToken) {
    try {
      const platform = Capacitor.getPlatform();
      await fetch(`${apiBaseUrl}/api/notifications/unregister`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          device_token: deviceToken,
          platform,
        }),
      });
    } catch (err) {
      console.error("[Push] トークン無効化失敗:", err);
    }
  }

  const { PushNotifications } = await import("@capacitor/push-notifications");
  await PushNotifications.removeAllListeners();
  console.log("[Push] リスナー解除完了");
}
