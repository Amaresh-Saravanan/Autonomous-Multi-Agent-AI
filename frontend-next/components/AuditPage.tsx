"use client";

import { Fragment, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { fetchAudit } from "@/lib/api";
import type { AuditEntry } from "@/lib/types";

// Audit trail (tracker 3.11.6.10 / BE-2, UX_DESIGN §3.3): admin-only
// accountability table. No filter/search UI yet — the entry volume from an
// in-memory dev-scale log doesn't need it; add when it does.
export default function AuditPage() {
  const { token, user } = useAuth();
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    fetchAudit(token)
      .then((data) => setEntries([...data].reverse()))
      .catch(() => setForbidden(true));
  }, [token]);

  if (forbidden || user?.role !== "admin") {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
          Audit trail is admin-only.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <h1 className="mb-console-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Audit Trail ({entries?.length ?? 0})
      </h1>
      <div className="overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
        <table className="w-full">
          <thead>
            <tr className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50">
              <th className="px-console-md py-console-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Timestamp
              </th>
              <th className="px-console-md py-console-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Actor
              </th>
              <th className="px-console-md py-console-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Action
              </th>
              <th className="px-console-md py-console-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Target
              </th>
            </tr>
          </thead>
          <tbody>
            {(entries ?? []).map((e, i) => (
              <Fragment key={i}>
                <tr
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  className="cursor-pointer border-b border-console-outline-variant/10 hover:bg-console-surface-container/40"
                >
                  <td className="px-console-md py-console-sm font-console-data-tabular text-[11px] text-console-on-surface-variant">
                    {e.timestamp}
                  </td>
                  <td className="px-console-md py-console-sm font-console-data-tabular text-console-data-tabular text-console-on-surface">
                    {e.actor}
                  </td>
                  <td className="px-console-md py-console-sm font-console-body-compact text-console-body-compact text-console-on-surface-variant">
                    {e.action}
                  </td>
                  <td className="px-console-md py-console-sm font-console-data-tabular text-[11px] text-console-outline">
                    {e.target}
                  </td>
                </tr>
                {expanded === i && (
                  <tr className="border-b border-console-outline-variant/10 bg-console-surface-container-low/30">
                    <td colSpan={4} className="px-console-md py-console-sm">
                      <div className="grid grid-cols-2 gap-console-md">
                        <div>
                          <div className="mb-1 font-console-label-caps text-[10px] uppercase text-console-outline">
                            Before
                          </div>
                          <pre className="overflow-x-auto font-console-data-tabular text-[10px] text-console-on-surface-variant">
                            {JSON.stringify(e.before, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div className="mb-1 font-console-label-caps text-[10px] uppercase text-console-outline">
                            After
                          </div>
                          <pre className="overflow-x-auto font-console-data-tabular text-[10px] text-console-on-surface-variant">
                            {JSON.stringify(e.after, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {entries?.length === 0 && (
              <tr>
                <td colSpan={4} className="px-console-md py-console-lg text-center font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                  No audit entries yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
