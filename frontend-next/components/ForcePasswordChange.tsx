"use client";

import { useAuth } from "@/lib/auth-context";
import ChangePasswordForm from "./ChangePasswordForm";

// Shown instead of the console while the account still has an admin-issued
// temporary password (the API refuses every other call until it is changed).
export default function ForcePasswordChange() {
  const { logout } = useAuth();
  return (
    <div className="flex min-h-screen w-screen items-center justify-center px-6 py-12" style={{ background: "var(--bg-base)" }}>
      <div className="glass-panel w-full max-w-md p-8">
        <div className="mb-3 text-xs font-bold tracking-[0.3em] text-(--accent) uppercase">EOC Platform</div>
        <h1 className="text-lg font-semibold text-(--text-primary)">Set a new password</h1>
        <p className="mt-1 mb-5 text-xs text-(--text-muted)">
          You signed in with a temporary password issued by an administrator. Choose your own to continue.
        </p>
        <ChangePasswordForm />
        <button onClick={logout} className="mt-5 block w-full cursor-pointer text-center text-xs text-(--text-muted) hover:text-(--text-primary)">
          Sign out
        </button>
      </div>
    </div>
  );
}
