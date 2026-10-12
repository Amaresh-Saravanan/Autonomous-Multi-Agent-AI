"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { approveAccessRequest, fetchAccessRequests, fetchAgencies, rejectAccessRequest } from "@/lib/api";
import type { AccessRequest, AgencyOption } from "@/lib/types";

// Admin queue for signup and password-reset requests (SEC-1). Approving shows
// the one-time temporary password HERE ONLY — the admin passes it to the user
// through a trusted channel; the API never stores or re-shows it.
export default function AccessPage() {
  const { token, user } = useAuth();
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [agencies, setAgencies] = useState<AgencyOption[]>([]);
  const [agencyFor, setAgencyFor] = useState<Record<string, string>>({});
  const [roleFor, setRoleFor] = useState<Record<string, string>>({});
  const [issued, setIssued] = useState<{ email: string; password: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetchAccessRequests(token).then(setRequests).catch(() => setError("Could not load requests."));
    fetchAgencies(token).then(setAgencies).catch(() => undefined);
  }, [token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  if (user?.role !== "admin") return null;

  async function approve(r: AccessRequest) {
    setError(null);
    try {
      const out = await approveAccessRequest(token, r.id, {
        agency_id: agencyFor[r.id] || agencies[0]?.id,
        role: roleFor[r.id] || undefined,
      });
      setIssued({ email: out.email, password: out.temporary_password });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approve failed.");
    }
  }

  async function reject(r: AccessRequest) {
    setError(null);
    try {
      await rejectAccessRequest(token, r.id);
      load();
    } catch {
      setError("Reject failed.");
    }
  }

  const pending = requests.filter((r) => r.status === "PENDING");
  const decided = requests.filter((r) => r.status !== "PENDING");
  const select =
    "rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-2 py-1 text-xs text-console-on-surface";

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <h1 className="mb-console-lg font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Access requests
      </h1>

      {issued && (
        <div role="status" className="mb-console-lg rounded-xl border border-console-primary/50 bg-console-primary/10 p-console-md">
          <p className="font-console-label-caps text-console-label-caps uppercase text-console-primary">Temporary password — shown once</p>
          <p className="mt-1 text-sm text-console-on-surface">
            {issued.email}: <code className="rounded bg-black/30 px-1.5 py-0.5 font-mono select-all">{issued.password}</code>
          </p>
          <p className="mt-1 text-xs text-console-on-surface-variant">
            Share it through a trusted channel. The user must set their own password at first sign-in.
          </p>
          <button onClick={() => setIssued(null)} className="mt-2 cursor-pointer text-xs text-console-primary underline">
            I have noted it — dismiss
          </button>
        </div>
      )}
      {error && <p role="alert" className="mb-console-md text-sm text-[var(--sev-critical)]">{error}</p>}

      <h2 className="mb-console-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
        Pending ({pending.length})
      </h2>
      <div className="mb-console-lg flex flex-col gap-2">
        {pending.map((r) => (
          <div key={r.id} className="rounded-md border border-console-outline-variant/30 bg-console-surface-container/60 p-console-md">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">{r.email}</span>
                <span className="ml-2 rounded bg-white/10 px-1.5 py-0.5 text-[10px] uppercase text-console-on-surface-variant">
                  {r.kind === "SIGNUP" ? "New account" : "Password reset"}
                </span>
              </div>
              <span className="text-[10px] text-console-outline">{r.created_at ? new Date(r.created_at).toLocaleString() : ""}</span>
            </div>
            {r.kind === "SIGNUP" && (
              <p className="mt-1 text-xs text-console-on-surface-variant">
                {r.full_name} · self-described agency: {r.agency_text || "—"} · asked for: {r.requested_role ?? "no preference"}
              </p>
            )}
            <div className="mt-console-sm flex flex-wrap items-center gap-2">
              {r.kind === "SIGNUP" && (
                <>
                  <select aria-label="Agency" className={select} value={agencyFor[r.id] ?? agencies[0]?.id ?? ""} onChange={(e) => setAgencyFor((m) => ({ ...m, [r.id]: e.target.value }))}>
                    {agencies.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                  <select aria-label="Role" className={select} value={roleFor[r.id] ?? r.requested_role ?? "VIEWER"} onChange={(e) => setRoleFor((m) => ({ ...m, [r.id]: e.target.value }))}>
                    <option value="VIEWER">Viewer</option>
                    <option value="OPERATOR">Operator</option>
                    <option value="ADMIN">Admin</option>
                  </select>
                </>
              )}
              <button onClick={() => approve(r)} className="cursor-pointer rounded-md border border-console-primary/40 bg-console-primary/10 px-3 py-1 text-xs text-console-primary hover:bg-console-primary/20">
                Approve
              </button>
              <button onClick={() => reject(r)} className="cursor-pointer rounded-md border border-[var(--sev-critical)]/40 bg-[var(--sev-critical)]/10 px-3 py-1 text-xs text-[var(--sev-critical)] hover:bg-[var(--sev-critical)]/20">
                Reject
              </button>
            </div>
          </div>
        ))}
        {pending.length === 0 && <p className="text-sm text-console-on-surface-variant">No pending requests.</p>}
      </div>

      {decided.length > 0 && (
        <>
          <h2 className="mb-console-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">History</h2>
          <div className="flex flex-col gap-1">
            {decided.map((r) => (
              <div key={r.id} className="flex justify-between rounded-md border border-console-outline-variant/20 px-console-md py-1.5 text-xs text-console-on-surface-variant">
                <span>{r.email} · {r.kind === "SIGNUP" ? "new account" : "reset"}</span>
                <span>{r.status.toLowerCase()}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
