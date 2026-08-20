"use client";

import { useAuth } from "@/lib/auth-context";
import ThemeToggle from "./ThemeToggle";

// Settings (tracker 3.11.6.11, UX_DESIGN §3.3): profile (from JWT claims,
// [UI-only]), theme, layout reset. Deliberately omits password change and
// notification preferences — auth.py has no mutation endpoints for either
// (tracker BE-6), and a form that posts nowhere is worse than no form.
export default function SettingsPage() {
  const { user, logout } = useAuth();

  function resetLayout() {
    try {
      localStorage.removeItem("dashboardLayout.v1");
    } catch {
      /* localStorage unavailable */
    }
    window.location.href = "/command";
  }

  if (!user) return null;

  return (
    <div className="h-full overflow-y-auto p-lg">
      <h1 className="mb-lg font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Settings
      </h1>

      <div className="max-w-lg rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-md shadow-lg backdrop-blur-xl">
        <h2 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
          Profile
        </h2>
        <div className="flex flex-col gap-sm font-console-body-compact text-console-body-compact">
          <div className="flex justify-between">
            <span className="text-console-on-surface-variant">Username</span>
            <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
              {user.username}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-console-on-surface-variant">Role</span>
            <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
              {user.role}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-console-on-surface-variant">Agency</span>
            <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
              {user.agency}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-lg max-w-lg rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-md shadow-lg backdrop-blur-xl">
        <h2 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
          Preferences
        </h2>
        <div className="flex items-center justify-between">
          <span className="font-console-body-compact text-console-body-compact text-console-on-surface-variant">
            Theme
          </span>
          <ThemeToggle />
        </div>
        <div className="mt-md flex items-center justify-between">
          <span className="font-console-body-compact text-console-body-compact text-console-on-surface-variant">
            Command dashboard layout
          </span>
          <button
            onClick={resetLayout}
            className="rounded-md border border-console-outline-variant/30 bg-console-surface-container/80 px-md py-sm font-console-label-caps text-console-label-caps text-console-on-surface hover:bg-console-surface-bright/80"
          >
            Reset to default
          </button>
        </div>
      </div>

      <div className="mt-lg max-w-lg">
        <button
          onClick={logout}
          className="rounded-md border border-[var(--sev-critical)]/40 bg-[var(--sev-critical)]/10 px-md py-sm font-console-label-caps text-console-label-caps text-[var(--sev-critical)] hover:bg-[var(--sev-critical)]/20"
        >
          Log out
        </button>
      </div>
    </div>
  );
}
