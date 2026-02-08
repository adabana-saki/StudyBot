/**
 * LoginScreen - Discord OAuth login screen.
 * Opens Discord OAuth in a WebBrowser and handles the callback.
 */
import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  StatusBar,
} from "react-native";
import { Colors } from "../constants/colors";
import { useAuth } from "../hooks/useAuth";

export default function LoginScreen() {
  const { login, isLoading, error } = useAuth();

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.background} />
      <View style={styles.container}>
        {/* Logo / Brand */}
        <View style={styles.brandContainer}>
          <View style={styles.logoCircle}>
            <Text style={styles.logoText}>{"\u{1F4DA}"}</Text>
          </View>
          <Text style={styles.title}>StudyBot</Text>
          <Text style={styles.subtitle}>Your AI Study Companion</Text>
        </View>

        {/* Feature highlights */}
        <View style={styles.features}>
          <FeatureRow
            icon={"\u{23F1}\u{FE0F}"}
            text="Pomodoro timer with focus tracking"
          />
          <FeatureRow
            icon={"\u{1F0CF}"}
            text="Spaced repetition flashcards"
          />
          <FeatureRow
            icon={"\u{1F3C6}"}
            text="Achievements and XP leveling"
          />
          <FeatureRow
            icon={"\u{1F4F1}"}
            text="Phone lock for distraction control"
          />
          <FeatureRow
            icon={"\u{1F49A}"}
            text="Wellness and mood tracking"
          />
        </View>

        {/* Login button */}
        <View style={styles.loginContainer}>
          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          <TouchableOpacity
            style={[styles.loginButton, isLoading && styles.loginButtonDisabled]}
            onPress={login}
            disabled={isLoading}
            activeOpacity={0.8}
          >
            {isLoading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Text style={styles.discordIcon}>{"\u{1F4AC}"}</Text>
                <Text style={styles.loginButtonText}>
                  Continue with Discord
                </Text>
              </>
            )}
          </TouchableOpacity>

          <Text style={styles.disclaimer}>
            Sign in with your Discord account to sync your study data across
            devices.
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

function FeatureRow({ icon, text }: { icon: string; text: string }) {
  return (
    <View style={styles.featureRow}>
      <Text style={styles.featureIcon}>{icon}</Text>
      <Text style={styles.featureText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  container: {
    flex: 1,
    paddingHorizontal: 24,
    justifyContent: "space-between",
    paddingTop: 60,
    paddingBottom: 40,
  },
  brandContainer: {
    alignItems: "center",
    marginBottom: 40,
  },
  logoCircle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: Colors.primary + "20",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
    borderWidth: 2,
    borderColor: Colors.primary + "40",
  },
  logoText: {
    fontSize: 40,
  },
  title: {
    fontSize: 36,
    fontWeight: "800",
    color: Colors.textPrimary,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: Colors.textSecondary,
  },
  features: {
    backgroundColor: Colors.card,
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  featureRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
  },
  featureIcon: {
    fontSize: 20,
    width: 36,
    textAlign: "center",
  },
  featureText: {
    fontSize: 15,
    color: Colors.textSecondary,
    flex: 1,
    marginLeft: 8,
  },
  loginContainer: {
    alignItems: "center",
  },
  errorContainer: {
    backgroundColor: Colors.error + "20",
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    width: "100%",
    borderWidth: 1,
    borderColor: Colors.error + "40",
  },
  errorText: {
    color: Colors.error,
    fontSize: 14,
    textAlign: "center",
  },
  loginButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 32,
    width: "100%",
    marginBottom: 16,
  },
  loginButtonDisabled: {
    opacity: 0.6,
  },
  discordIcon: {
    fontSize: 20,
    marginRight: 10,
  },
  loginButtonText: {
    color: "#fff",
    fontSize: 17,
    fontWeight: "700",
  },
  disclaimer: {
    fontSize: 12,
    color: Colors.textDisabled,
    textAlign: "center",
    lineHeight: 18,
    paddingHorizontal: 20,
  },
});
