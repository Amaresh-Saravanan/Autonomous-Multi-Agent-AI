"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { changePassword } from "@/lib/api";

// Shared by Settings and the forced first-login screen.
export default function ChangePasswordForm({ onDone }: { onDone?: () => void }) {
  const { token, markPasswordChanged } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (next !== confirm) return setError("New passwords do not match.");
    setBusy(true);
    try {
      await changePassword(token, current, next);
      markPasswordChanged();
      setDone(true);
      setCurrent("");
      setNext("");
      setConfirm("");
      onDone?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password.");
    } finally {
      setBusy(false);
    }
  }

  const input =
    "w-full rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-2.5 py-2 text-sm text-console-on-surface";

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-xs text-console-on-surface-variant">
        Current password
        <input required type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} className={input} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-console-on-surface-variant">
        New password (10+ characters)
        <input required minLength={10} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} className={input} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-console-on-surface-variant">
        Confirm new password
        <input required minLength={10} type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className={input} />
      </label>
      {error && <p role="alert" className="text-xs text-[var(--sev-critical)]">{error}</p>}
      {done && <p role="status" className="text-xs text-console-primary">Password changed.</p>}
      <button
        type="submit"
        disabled={busy}
        className="cursor-pointer rounded-md border border-console-primary/40 bg-console-primary/10 px-console-md py-console-sm font-console-label-caps text-console-label-caps text-console-primary hover:bg-console-primary/20 disabled:opacity-50"
      >
        {busy ? "Saving…" : "Change password"}
      </button>
    </form>
  );
}
