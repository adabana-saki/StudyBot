/**
 * Authentication context and provider.
 * Manages login state, token lifecycle, and user profile.
 */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import {
  storeTokens,
  clearTokens,
  getAccessToken,
  hasTokens,
  storeUserId,
} from "../lib/auth";
import { getProfile, UserProfile } from "../lib/api";
import { registerDeviceToken } from "../lib/notifications";
import { DISCORD_AUTH_URL } from "../constants/config";

// Ensure WebBrowser auth sessions are properly cleaned up
WebBrowser.maybeCompleteAuthSession();

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserProfile | null;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isAuthenticated: false,
    user: null,
    error: null,
  });

  /**
   * Check for existing tokens on mount and load user profile if found.
   */
  useEffect(() => {
    let cancelled = false;

    async function initAuth() {
      try {
        const tokensExist = await hasTokens();
        if (!tokensExist) {
          if (!cancelled) {
            setState({
              isLoading: false,
              isAuthenticated: false,
              user: null,
              error: null,
            });
          }
          return;
        }

        const profile = await getProfile();
        if (!cancelled) {
          setState({
            isLoading: false,
            isAuthenticated: true,
            user: profile,
            error: null,
          });
        }
      } catch {
        // Token might be invalid; clear and show login
        await clearTokens();
        if (!cancelled) {
          setState({
            isLoading: false,
            isAuthenticated: false,
            user: null,
            error: null,
          });
        }
      }
    }

    initAuth();
    return () => {
      cancelled = true;
    };
  }, []);

  /**
   * Listen for deep link callbacks from the OAuth flow.
   */
  useEffect(() => {
    const subscription = Linking.addEventListener("url", handleDeepLink);
    return () => {
      subscription.remove();
    };
  }, []);

  /**
   * Handle the deep link callback from Discord OAuth.
   * Expected URL: studybot://auth/callback?access_token=...&refresh_token=...
   */
  const handleDeepLink = useCallback(async (event: { url: string }) => {
    const { url } = event;
    if (!url.includes("auth/callback")) return;

    try {
      const parsed = Linking.parse(url);
      const accessToken = parsed.queryParams?.access_token as
        | string
        | undefined;
      const refreshToken = parsed.queryParams?.refresh_token as
        | string
        | undefined;

      if (!accessToken || !refreshToken) {
        setState((prev) => ({
          ...prev,
          error: "Invalid authentication response.",
          isLoading: false,
        }));
        return;
      }

      await storeTokens(accessToken, refreshToken);

      // Fetch user profile
      const profile = await getProfile();
      await storeUserId(profile.user_id);

      setState({
        isLoading: false,
        isAuthenticated: true,
        user: profile,
        error: null,
      });

      // Register push notifications after successful login
      registerDeviceToken().catch(console.error);
    } catch (error) {
      setState((prev) => ({
        ...prev,
        error: "Failed to complete login. Please try again.",
        isLoading: false,
      }));
    }
  }, []);

  /**
   * Initiate the Discord OAuth login flow.
   */
  const login = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await WebBrowser.openAuthSessionAsync(
        DISCORD_AUTH_URL,
        "studybot://auth/callback"
      );

      if (result.type === "cancel" || result.type === "dismiss") {
        setState((prev) => ({ ...prev, isLoading: false }));
        return;
      }

      // If we got a URL back directly (some platforms), handle it
      if (result.type === "success" && result.url) {
        await handleDeepLink({ url: result.url });
      }
    } catch {
      setState((prev) => ({
        ...prev,
        error: "Failed to open login page.",
        isLoading: false,
      }));
    }
  }, [handleDeepLink]);

  /**
   * Log out: clear tokens and reset state.
   */
  const logout = useCallback(async () => {
    await clearTokens();
    setState({
      isLoading: false,
      isAuthenticated: false,
      user: null,
      error: null,
    });
  }, []);

  /**
   * Refresh the user profile from the API.
   */
  const refreshProfile = useCallback(async () => {
    try {
      const profile = await getProfile();
      setState((prev) => ({
        ...prev,
        user: profile,
        error: null,
      }));
    } catch {
      // If refresh fails with auth error, log out
      setState((prev) => ({
        ...prev,
        error: "Failed to refresh profile.",
      }));
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      login,
      logout,
      refreshProfile,
    }),
    [state, login, logout, refreshProfile]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access authentication state and methods.
 * Must be used within an AuthProvider.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
