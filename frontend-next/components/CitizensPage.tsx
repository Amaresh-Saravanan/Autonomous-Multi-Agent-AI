"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { fetchCitizenReports, postCitizenChat } from "@/lib/api";
import type { CitizenReport } from "@/lib/types";

interface ChatMessage {
  role: "citizen" | "ag7";
  text: string;
}

// Citizen report review + AG-7 chat (tracker 3.11.6.8, UX_DESIGN §3.3
// Citizens). The chat panel is new UI, not a reskin — POST /citizen/chat
// (AG-7, keyword-RAG + optional LLM) had zero frontend caller anywhere in
// the app before this. Chat history is local/ephemeral (no GET endpoint
// for past conversations exists) — each session starts fresh, which
// matches how a real citizen's session would behave anyway (no login).
export default function CitizensPage() {
  const { token } = useAuth();
  const [reports, setReports] = useState<CitizenReport[]>([]);
  const [filter, setFilter] = useState<"all" | "flagged" | "high-severity" | "low-trust">("all");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchCitizenReports(token).then(setReports).catch(console.error);
  }, [token]);

  const filtered = useMemo(() => {
    return reports.filter((r) => {
      if (filter === "flagged") return r.flagged_for_review;
      if (filter === "high-severity") return r.claimed_severity >= 0.7;
      if (filter === "low-trust") return r.confidence < 0.5;
      return true;
    });
  }, [reports, filter]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { role: "citizen", text }]);
    setDraft("");
    setSending(true);
    try {
      const reply = await postCitizenChat(text);
      setMessages((prev) => [...prev, { role: "ag7", text: reply.reply }]);
    } catch {
      setMessages((prev) => [...prev, { role: "ag7", text: "Sorry, I couldn't reach the assistant." }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="grid h-full grid-cols-1 gap-lg overflow-hidden p-lg lg:grid-cols-2">
      {/* Reports column */}
      <div className="flex flex-col overflow-hidden">
        <h1 className="mb-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
          Citizen Reports ({filtered.length})
        </h1>
        <div className="mb-md flex gap-1">
          {(["all", "flagged", "high-severity", "low-trust"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-sm py-sm font-console-label-caps text-[10px] uppercase transition-colors ${
                filter === f
                  ? "bg-console-primary/20 text-console-primary"
                  : "text-console-on-surface-variant hover:bg-console-surface-container/40"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto pr-1">
          {filtered.map((r) => (
            <div
              key={r.event_id}
              className="mb-sm rounded-md border border-console-outline-variant/20 bg-console-surface-container/60 px-md py-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                  {r.reporter_id}
                </span>
                {r.flagged_for_review && (
                  <span className="font-console-label-caps text-[9px] font-bold text-[var(--sev-critical)]">
                    ⚠ FLAGGED
                  </span>
                )}
              </div>
              <p className="mt-1 font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                {r.message}
              </p>
              <p className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
                claimed severity {r.claimed_severity.toFixed(2)} · trust {r.confidence.toFixed(2)}
              </p>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
              No reports match this filter.
            </div>
          )}
        </div>
      </div>

      {/* AG-7 chat column */}
      <div className="flex flex-col overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
        <div className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50 px-md py-sm">
          <h2 className="font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            AG-7 Citizen Assistance
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto p-md">
          {messages.map((m, i) => (
            <div key={i} className={`mb-sm flex ${m.role === "citizen" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-md px-sm py-sm font-console-body-sm text-console-body-sm ${
                  m.role === "citizen"
                    ? "bg-console-primary/20 text-console-on-surface"
                    : "bg-console-surface-container/60 text-console-on-surface-variant"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          {messages.length === 0 && (
            <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
              Ask AG-7 for guidance — e.g. &quot;What should I do during a flood warning?&quot;
            </div>
          )}
        </div>
        <form onSubmit={handleSend} className="flex gap-sm border-t border-console-outline-variant/20 p-sm">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Type a message…"
            disabled={sending}
            className="flex-1 rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-sm py-sm font-console-body-compact text-console-body-compact text-console-on-surface placeholder:text-console-outline focus:border-console-primary focus:outline-none"
          />
          <button
            type="submit"
            disabled={sending}
            className="rounded-md bg-console-primary px-md py-sm font-console-label-caps text-console-label-caps text-console-on-primary transition-colors hover:bg-console-primary-container disabled:opacity-50"
          >
            {sending ? "…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
