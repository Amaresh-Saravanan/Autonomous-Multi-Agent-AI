"use client";

import { useAuth } from "@/lib/auth-context";

export default function WhoAmI({
  editMode,
  onToggleEdit,
}: {
  editMode: boolean;
  onToggleEdit: () => void;
}) {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <div className="glass-panel absolute top-4 right-4 z-40 flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-muted)]">
      <button
        onClick={onToggleEdit}
        aria-pressed={editMode}
        className={`cursor-pointer rounded border px-1.5 py-0.5 ${
          editMode
            ? "border-[var(--accent)] bg-[var(--accent)]/20 text-[var(--text-primary)]"
            : "border-[var(--border)] bg-white/5 text-[var(--text-primary)] hover:bg-white/15"
        }`}
      >
        {editMode ? "Lock layout" : "Edit layout"}
      </button>
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
