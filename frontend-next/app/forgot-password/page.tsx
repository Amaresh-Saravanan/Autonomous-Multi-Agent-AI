"use client";

import { useState, type FormEvent } from "react";
import AuthPageShell from "@/components/AuthPageShell";
import { postResetRequest } from "@/lib/api";

// PRD UI-8. No email service is part of v1, so a reset is a request that an
// administrator fulfils with a temporary password. The acknowledgement is the
// same whether or not the account exists.
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error" | "limited">("idle");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setState("sending");
    try {
      await postResetRequest(email);
      setState("sent");
    } catch (err) {
      setState(String(err).includes("429") ? "limited" : "error");
    }
  }

  const input = "w-full rounded-md border border-(--border) bg-white/5 px-2.5 py-2 text-sm text-(--text-primary)";

  return (
    <AuthPageShell
      title="Reset your password"
      subtitle="An administrator will issue a temporary password after confirming your identity."
    >
      {state === "sent" ? (
        <p role="status" className="text-sm text-(--text-primary)">
          If that email belongs to an account, a reset request has been sent to your administrator. They will contact you
          through your agency&apos;s usual channel.
        </p>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
            Work email
            <input required type="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} className={input} autoComplete="email" />
          </label>
          {state === "error" && <p role="alert" className="text-xs text-(--sev-critical)">Could not send the request. Contact your administrator directly.</p>}
          {state === "limited" && <p role="alert" className="text-xs text-(--sev-critical)">Too many requests. Please wait a few minutes.</p>}
          <button
            type="submit"
            disabled={state === "sending"}
            className="cursor-pointer rounded-md border border-(--accent) bg-(--accent)/20 py-2 text-sm font-medium hover:bg-(--accent)/30 disabled:opacity-50"
          >
            {state === "sending" ? "Sending…" : "Request reset"}
          </button>
        </form>
      )}
    </AuthPageShell>
  );
}
