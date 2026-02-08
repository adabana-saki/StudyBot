/**
 * AppNavigator - Root navigation setup using React Navigation.
 * Combines a bottom tab navigator (main screens) with a native stack
 * for full-screen views. Shows LoginScreen when not authenticated.
 */
import React from "react";
import { ActivityIndicator, View, Text, StyleSheet } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Colors } from "../constants/colors";
import { useAuth } from "../hooks/useAuth";

// Screens
import LoginScreen from "../screens/LoginScreen";
import DashboardScreen from "../screens/DashboardScreen";
import StudyTimerScreen from "../screens/StudyTimerScreen";
import PhoneLockScreen from "../screens/PhoneLockScreen";
import FlashcardScreen from "../screens/FlashcardScreen";
import AchievementsScreen from "../screens/AchievementsScreen";
import WellnessScreen from "../screens/WellnessScreen";
import SettingsScreen from "../screens/SettingsScreen";

// ─── Type definitions ─────────────────────────────────────────────────────────

export type RootStackParamList = {
  Login: undefined;
  MainTabs: undefined;
  StudyTimer: undefined;
  PhoneLock: undefined;
  Flashcards: undefined;
  Wellness: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Achievements: undefined;
  Settings: undefined;
};

// ─── Navigators ───────────────────────────────────────────────────────────────

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

// ─── Tab Icon ─────────────────────────────────────────────────────────────────

function TabIcon({ emoji, size }: { emoji: string; size: number }) {
  return (
    <Text style={{ fontSize: size - 4, textAlign: "center" }}>{emoji}</Text>
  );
}

// ─── Tab Navigator ────────────────────────────────────────────────────────────

function MainTabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: {
          backgroundColor: Colors.card,
          borderTopColor: Colors.border,
          borderTopWidth: 1,
          height: 60,
          paddingBottom: 8,
          paddingTop: 4,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textDisabled,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
        headerStyle: {
          backgroundColor: Colors.background,
        },
        headerTintColor: Colors.textPrimary,
        headerTitleStyle: {
          fontWeight: "700",
        },
        headerShadowVisible: false,
      }}
    >
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: "Dashboard",
          tabBarIcon: ({ size }) => (
            <TabIcon emoji={"\u{1F3E0}"} size={size} />
          ),
          headerTitle: "StudyBot",
        }}
      />
      <Tab.Screen
        name="Achievements"
        component={AchievementsScreen}
        options={{
          title: "Achievements",
          tabBarIcon: ({ size }) => (
            <TabIcon emoji={"\u{1F3C6}"} size={size} />
          ),
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: "Settings",
          tabBarIcon: ({ size }) => (
            <TabIcon emoji={"\u{2699}\u{FE0F}"} size={size} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// ─── Root Navigator ───────────────────────────────────────────────────────────

export default function AppNavigator() {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading screen while checking auth state
  if (isLoading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer
      theme={{
        dark: true,
        colors: {
          primary: Colors.primary,
          background: Colors.background,
          card: Colors.card,
          text: Colors.textPrimary,
          border: Colors.border,
          notification: Colors.primary,
        },
        fonts: {
          regular: { fontFamily: "System", fontWeight: "400" },
          medium: { fontFamily: "System", fontWeight: "500" },
          bold: { fontFamily: "System", fontWeight: "700" },
          heavy: { fontFamily: "System", fontWeight: "800" },
        },
      }}
    >
      <Stack.Navigator
        screenOptions={{
          headerStyle: {
            backgroundColor: Colors.background,
          },
          headerTintColor: Colors.textPrimary,
          headerTitleStyle: {
            fontWeight: "700",
          },
          headerShadowVisible: false,
          contentStyle: {
            backgroundColor: Colors.background,
          },
          animation: "slide_from_right",
        }}
      >
        {isAuthenticated ? (
          <>
            <Stack.Screen
              name="MainTabs"
              component={MainTabNavigator}
              options={{ headerShown: false }}
            />
            <Stack.Screen
              name="StudyTimer"
              component={StudyTimerScreen}
              options={{ title: "Study Timer" }}
            />
            <Stack.Screen
              name="PhoneLock"
              component={PhoneLockScreen}
              options={{ title: "Phone Lock" }}
            />
            <Stack.Screen
              name="Flashcards"
              component={FlashcardScreen}
              options={{ title: "Flashcards", headerShown: false }}
            />
            <Stack.Screen
              name="Wellness"
              component={WellnessScreen}
              options={{ title: "Wellness" }}
            />
          </>
        ) : (
          <Stack.Screen
            name="Login"
            component={LoginScreen}
            options={{ headerShown: false }}
          />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
  },
});
