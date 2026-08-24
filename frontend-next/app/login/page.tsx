"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import ThemeToggle from "@/components/ThemeToggle";

// Dedicated login page (tracker 3.11.2) — split-screen per UX_DESIGN.md
// §3.1, replaces the old in-dashboard LoginOverlay gate. Successful login
// redirects to /command for every role; role-specific landing pages
// (medical -> /medical, field coordinator -> /routes) are noted in the
// spec as a future default once those pages exist (tracker 3.11.6).
export default function LoginPage() {
  const { user, login, loginError } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) router.replace("/command");
  }, [user, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    await login(username, password);
    setSubmitting(false);
  }

  if (user) return null;

  return (
    <div className="relative flex min-h-screen w-screen" style={{ background: "var(--bg-base)" }}>
      <div className="absolute right-4 top-4 z-20">
        <ThemeToggle />
      </div>
      {/* Mission visual — decorative only, no live map data on a public route */}
      <div className="relative hidden flex-1 items-center justify-center overflow-hidden border-r border-(--border) lg:flex">
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(circle at 30% 40%, rgba(59,130,246,0.18), transparent 55%), radial-gradient(circle at 70% 70%, rgba(239,68,68,0.12), transparent 50%)",
          }}
        />
        <svg className="absolute inset-0 h-full w-full opacity-20" aria-hidden="true">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--border)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
        <div className="relative z-10 min-w-0 max-w-sm px-8 text-center">
          <div className="mb-3 text-xs font-bold tracking-[0.3em] text-(--accent) uppercase">
            EOC Platform
          </div>
          <h1 className="text-2xl font-semibold text-(--text-primary)">
            Autonomous multi-agent disaster response
          </h1>
          <p className="mt-3 text-sm text-(--text-muted)">
            Every recommendation carries evidence and rationale. Humans stay in the loop.
          </p>
        </div>
      </div>

      {/* Form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="glass-panel w-full max-w-sm p-8">
          <h2 className="text-lg font-semibold text-(--text-primary)">Sign in</h2>
          <p className="mt-1 text-xs text-(--text-muted)">
            Enter your command center credentials.
          </p>
          <div className="mt-4 min-h-4 text-xs text-(--sev-critical)">
            {loginError}
          </div>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <label className="flex w-full flex-col gap-1 text-xs text-(--text-muted)">
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                className="w-full rounded-md border border-(--border) bg-white/5 px-2.5 py-2 text-sm text-(--text-primary)"
              />
            </label>
            <label className="flex w-full flex-col gap-1 text-xs text-(--text-muted)">
              Password
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                autoComplete="current-password"
                className="w-full rounded-md border border-(--border) bg-white/5 px-2.5 py-2 text-sm text-(--text-primary)"
              />
            </label>
            <button
              type="submit"
              disabled={submitting}
              className="mt-1 cursor-pointer rounded-md border border-(--accent) bg-(--accent)/20 py-2 text-sm font-medium text-(--text-primary) hover:bg-(--accent)/30 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Log in"}
            </button>
          </form>
          <p className="mt-5 text-center text-xs text-(--text-muted)">
            New agency?{" "}
            <span className="text-(--text-primary)">
              Contact your administrator for access.
            </span>
          </p>
          <Link
            href="/"
            className="mt-3 block text-center text-xs text-(--text-muted) hover:text-(--text-primary)"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
