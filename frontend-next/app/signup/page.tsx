"use client";

import { useState, type FormEvent } from "react";
import AuthPageShell from "@/components/AuthPageShell";
import { postAccessRequest } from "@/lib/api";

// PRD UI-8 / SEC-1. Submitting queues a request for an administrator; no
// account exists until one approves it, and the acknowledgement is identical
// whether or not the email is already registered.
export default function SignupPage() {
  const [name, setName] = useState("");
  const [agency, setAgency] = useState("");
  const [role, setRole] = useState<"OPERATOR" | "VIEWER">("VIEWER");
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error" | "limited">("idle");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setState("sending");
    try {
      await postAccessRequest({ email, full_name: name, agency_text: agency || undefined, requested_role: role });
      setState("sent");
    } catch (err) {
      setState(String(err).includes("429") ? "limited" : "error");
    }
  }

  const input = "w-full rounded-md border border-(--border) bg-white/5 px-2.5 py-2 text-sm text-(--text-primary)";

  return (
    <AuthPageShell
      title="Request access"
      subtitle="An administrator reviews every request. You will receive a temporary password from them."
    >
      {state === "sent" ? (
        <p role="status" className="text-sm text-(--text-primary)">
          Request received. If it is approved, your administrator will give you a temporary password and you will be asked to
          change it at first sign-in.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
            Full name
            <input required minLength={2} maxLength={200} value={name} onChange={(e) => setName(e.target.value)} className={input} autoComplete="name" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
            Agency
            <input maxLength={200} value={agency} onChange={(e) => setAgency(e.target.value)} className={input} />
          </label>
          <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
            Work email
            <input required type="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} className={input} autoComplete="email" />
          </label>
          <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
            Access needed
            <select value={role} onChange={(e) => setRole(e.target.value as "OPERATOR" | "VIEWER")} className={input}>
              <option value="VIEWER">Viewer — read-only</option>
              <option value="OPERATOR">Operator — approve / reject recommendations</option>
            </select>
          </label>
          {state === "error" && <p role="alert" className="text-xs text-(--sev-critical)">Could not send the request. Try again, or contact your administrator.</p>}
          {state === "limited" && <p role="alert" className="text-xs text-(--sev-critical)">Too many requests. Please wait a few minutes.</p>}
          <button
            type="submit"
            disabled={state === "sending"}
            className="mt-1 cursor-pointer rounded-md border border-(--accent) bg-(--accent)/20 py-2 text-sm font-medium hover:bg-(--accent)/30 disabled:opacity-50"
          >
            {state === "sending" ? "Sending…" : "Send request"}
          </button>
        </form>
      )}
    </AuthPageShell>
  );
}
