const TOKEN_KEY = "studybot_token";
const REFRESH_TOKEN_KEY = "studybot_refresh_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function removeRefreshToken(): void {
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  const token = getToken();
  if (!token) return false;

  try {
    // JWT tokens are base64url encoded: header.payload.signature
    const payload = JSON.parse(atob(token.split(".")[1]));
    const now = Math.floor(Date.now() / 1000);
    // Check if token is expired (with 60s buffer)
    if (payload.exp && payload.exp < now + 60) {
      return false;
    }
    return true;
  } catch {
    // If we can't decode it, treat it as valid (non-JWT token)
    return true;
  }
}

export function logout(): void {
  removeToken();
  removeRefreshToken();
  window.location.href = "/";
}
