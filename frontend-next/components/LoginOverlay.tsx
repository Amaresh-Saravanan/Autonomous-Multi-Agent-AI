"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";

export default function LoginOverlay() {
  const { login, loginError } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await login(username, password);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-(--bg-base)">
      <div className="glass-panel w-72 p-6">
        <h2 className="mb-4 text-base font-semibold">EOC Dashboard login</h2>
        <div className="mb-2 min-h-3.5 text-xs text-(--sev-critical)">
          {loginError}
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-2.5">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
            autoComplete="username"
            className="rounded-md border border-(--border) bg-white/5 px-2 py-1.5 text-(--text-primary)"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="password"
            autoComplete="current-password"
            className="rounded-md border border-(--border) bg-white/5 px-2 py-1.5 text-(--text-primary)"
          />
          <button
            type="submit"
            className="cursor-pointer rounded-md border border-(--border) bg-white/8 py-2 text-(--text-primary) hover:bg-white/15"
          >
            Log in
          </button>
        </form>
      </div>
    </div>
  );
}
