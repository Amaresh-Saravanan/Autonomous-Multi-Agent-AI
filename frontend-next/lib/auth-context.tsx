"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AUTH_EXPIRED_EVENT, login as apiLogin } from "./api";
import type { CurrentUser } from "./types";

interface AuthContextValue {
  token: string | null;
  user: CurrentUser | null;
  loginError: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  markPasswordChanged: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = "authToken";
const USER_KEY = "currentUser";

function readSession(): { token: string; user: CurrentUser } | null {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const raw = localStorage.getItem(USER_KEY);
    if (!token || !raw) return null;
    const user = JSON.parse(raw) as CurrentUser;
    // Drop sessions whose JWT has already expired (exp is epoch seconds).
    if (!user.exp || user.exp * 1000 <= Date.now()) return null;
    return { token, user };
  } catch {
    return null;
  }
}

function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    /* storage unavailable (private mode) — nothing to clear */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // localStorage only exists client-side, so the session is restored after
  // mount. This is the one legitimate "sync external store into state" effect.
  useEffect(() => {
    const session = readSession();
    if (session) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setToken(session.token);
      setUser(session.user);
    } else {
      clearSession();
    }
    setHydrated(true);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setToken(null);
    setUser(null);
  }, []);

  // The API client signals a 401 (expired/revoked token); drop the session so
  // the console layout redirects to /login. Also expire on the JWT's own clock.
  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, logout);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, logout);
  }, [logout]);

  useEffect(() => {
    if (!user) return;
    const ms = user.exp * 1000 - Date.now();
    // setTimeout(…, 0) also covers "already expired" without a sync setState.
    const id = setTimeout(logout, Math.min(Math.max(ms, 0), 2 ** 31 - 1));
    return () => clearTimeout(id);
  }, [user, logout]);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const { accessToken, user: nextUser } = await apiLogin(email.trim(), password);
      try {
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
      } catch {
        /* storage unavailable — session lasts until reload */
      }
      setToken(accessToken);
      setUser(nextUser);
      setLoginError(null);
    } catch {
      setLoginError("Sign-in failed — check your email and password.");
    }
  }, []);

  const markPasswordChanged = useCallback(() => {
    setUser((u) => {
      if (!u) return u;
      const next = { ...u, mustChangePassword: false };
      try {
        localStorage.setItem(USER_KEY, JSON.stringify(next));
      } catch {
        /* storage unavailable */
      }
      return next;
    });
  }, []);

  if (!hydrated) return null;

  return (
    <AuthContext.Provider value={{ token, user, loginError, login, logout, markPasswordChanged }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
