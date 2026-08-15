"use client";

import { useAuth } from "@/lib/auth-context";

export default function WhoAmI() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="glass-panel absolute top-4 right-[372px] z-40 flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-muted)]">
      <span>
        {user.username} ({user.role})
      </span>
      <button
        onClick={logout}
        className="cursor-pointer rounded border border-[var(--border)] bg-white/5 px-1.5 py-0.5 text-[var(--text-primary)] hover:bg-white/15"
      >
        Log out
      </button>
    </div>
  );
}
