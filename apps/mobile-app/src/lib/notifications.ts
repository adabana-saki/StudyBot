/**
 * Expo Push Notifications setup and helpers.
 * Handles permission requests, token registration, and notification handling.
 */
import { Platform } from "react-native";
import * as Notifications from "expo-notifications";
import { registerPushToken } from "./api";

/**
 * Configure how notifications behave when the app is in the foreground.
 */
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

/**
 * Request notification permissions and return the Expo push token.
 * Returns null if permissions are denied.
 */
export async function requestPushPermissions(): Promise<string | null> {
  const { status: existingStatus } =
    await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.warn("[Notifications] Permission not granted.");
    return null;
  }

  // Android requires a notification channel
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "Default",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#5865F2",
    });

    await Notifications.setNotificationChannelAsync("timer", {
      name: "Study Timer",
      description: "Notifications for Pomodoro timer events",
      importance: Notifications.AndroidImportance.HIGH,
      sound: "default",
    });

    await Notifications.setNotificationChannelAsync("phone-lock", {
      name: "Phone Lock",
      description: "Notifications for phone lock mode",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 500, 250, 500],
    });
  }

  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    return tokenData.data;
  } catch (error) {
    console.error("[Notifications] Failed to get push token:", error);
    return null;
  }
}

/**
 * Register the device push token with the backend.
 */
export async function registerDeviceToken(): Promise<void> {
  const token = await requestPushPermissions();
  if (!token) return;

  const platform = Platform.OS === "ios" ? "ios" : "android";
  try {
    await registerPushToken(token, platform as "ios" | "android");
    console.log("[Notifications] Device token registered with backend.");
  } catch (error) {
    console.error("[Notifications] Failed to register token:", error);
  }
}

/**
 * Schedule a local notification (e.g., timer complete).
 */
export async function scheduleLocalNotification(options: {
  title: string;
  body: string;
  data?: Record<string, unknown>;
  triggerSeconds?: number;
  channelId?: string;
}): Promise<string> {
  const {
    title,
    body,
    data = {},
    triggerSeconds,
    channelId = "default",
  } = options;

  const trigger = triggerSeconds
    ? { seconds: triggerSeconds, type: "timeInterval" as const }
    : null;

  const id = await Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      data,
      sound: "default",
      ...(Platform.OS === "android" ? { channelId } : {}),
    },
    trigger,
  });

  return id;
}

/**
 * Cancel a previously scheduled notification.
 */
export async function cancelNotification(
  notificationId: string
): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(notificationId);
}

/**
 * Cancel all scheduled notifications.
 */
export async function cancelAllNotifications(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}

/**
 * Add a listener for notifications received while the app is foregrounded.
 */
export function addNotificationReceivedListener(
  handler: (notification: Notifications.Notification) => void
): Notifications.Subscription {
  return Notifications.addNotificationReceivedListener(handler);
}

/**
 * Add a listener for when the user taps on a notification.
 */
export function addNotificationResponseListener(
  handler: (response: Notifications.NotificationResponse) => void
): Notifications.Subscription {
  return Notifications.addNotificationResponseReceivedListener(handler);
}

/**
 * Get the badge count (iOS only).
 */
export async function getBadgeCount(): Promise<number> {
  return Notifications.getBadgeCountAsync();
}

/**
 * Set the badge count (iOS only).
 */
export async function setBadgeCount(count: number): Promise<void> {
  await Notifications.setBadgeCountAsync(count);
}
