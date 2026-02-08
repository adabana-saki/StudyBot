/**
 * App.tsx - Root component for StudyBot Mobile.
 * Wraps the app in providers and sets up the status bar.
 */
import React, { useEffect } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider } from "./src/hooks/useAuth";
import AppNavigator from "./src/navigation/AppNavigator";
import {
  addNotificationReceivedListener,
  addNotificationResponseListener,
} from "./src/lib/notifications";

export default function App() {
  // Set up notification listeners at the app root
  useEffect(() => {
    const receivedSubscription = addNotificationReceivedListener(
      (notification) => {
        console.log(
          "[App] Notification received:",
          notification.request.content.title
        );
      }
    );

    const responseSubscription = addNotificationResponseListener((response) => {
      const data = response.notification.request.content.data;
      console.log("[App] Notification tapped:", data);

      // Handle navigation based on notification data
      // e.g., navigate to a specific screen based on data.screen
    });

    return () => {
      receivedSubscription.remove();
      responseSubscription.remove();
    };
  }, []);

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="light" />
        <AppNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
