"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { decodeJwtPayload, login as apiLogin } from "./api";
import type { CurrentUser } from "./types";

interface AuthContextValue {
  token: string | null;
  user: CurrentUser | null;
  loginError: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // localStorage only exists client-side, so hydrate after mount.
  useEffect(() => {
    const storedToken = localStorage.getItem("authToken");
    const storedUser = localStorage.getItem("currentUser");
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setHydrated(true);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const accessToken = await apiLogin(username, password);
      const payload = decodeJwtPayload(accessToken);
      localStorage.setItem("authToken", accessToken);
      localStorage.setItem("currentUser", JSON.stringify(payload));
      setToken(accessToken);
      setUser(payload);
      setLoginError(null);
    } catch {
      setLoginError("Login failed — check username/password.");
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("currentUser");
    setToken(null);
    setUser(null);
  }, []);

  if (!hydrated) return null;

  return (
    <AuthContext.Provider value={{ token, user, loginError, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
