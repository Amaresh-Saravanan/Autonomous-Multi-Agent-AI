"use client";

import { useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { postCitizenChat, postCitizenReport } from "@/lib/api";
import ThemeToggle from "@/components/ThemeToggle";

// Public citizen help (PRD UI-6): multilingual assistant + incident report.
// No login — citizens aren't platform users. Both calls go through same-origin
// server routes that hold the device credential; reports are trust-scored by
// the backend and reviewed by operators, never acted on automatically.
const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "ta", label: "தமிழ்" },
  { code: "te", label: "తెలుగు" },
  { code: "bn", label: "বাংলা" },
  { code: "mr", label: "मराठी" },
];

interface Msg {
  role: "you" | "assistant";
  text: string;
  note?: string;
}

export default function CitizenPage() {
  const [language, setLanguage] = useState("en");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [reportText, setReportText] = useState("");
  const [severity, setSeverity] = useState(0.5);
  const [contact, setContact] = useState("");
  const [reportState, setReportState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [limited, setLimited] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  async function send(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    setMessages((m) => [...m, { role: "you", text }]);
    setDraft("");
    setSending(true);
    try {
      const reply = await postCitizenChat(text, language);
      setMessages((m) => [...m, {
        role: "assistant",
        text: reply.reply,
        note: reply.language_fallback ? "This answer is not available in your selected language yet." : undefined,
      }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: "The assistant is unavailable right now. If you are in danger, call your local emergency number." },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  async function report(e: FormEvent) {
    e.preventDefault();
    if (!reportText.trim() || reportState === "sending") return;
    setReportState("sending");
    setLimited(false);
    try {
      let coords: { lat?: number; lon?: number } = {};
      if ("geolocation" in navigator) {
        coords = await new Promise((resolve) =>
          navigator.geolocation.getCurrentPosition(
            (p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }),
            () => resolve({}),
            { timeout: 4000 }
          )
        );
      }
      await postCitizenReport({
        message: reportText.trim(),
        claimed_severity: severity,
        reporter_contact: contact.trim() || undefined,
        ...coords,
      });
      setReportState("sent");
      setReportText("");
    } catch (err) {
      setLimited(String(err).includes("429"));
      setReportState("error");
    }
  }

  const input = "w-full rounded-md border border-(--border) bg-white/5 px-2.5 py-2 text-sm text-(--text-primary)";

  return (
    <div className="min-h-screen px-4 py-8" style={{ background: "var(--bg-base)" }}>
      <div className="absolute right-4 top-4"><ThemeToggle /></div>
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="text-xs text-(--text-muted) hover:text-(--text-primary)">← Home</Link>
        <h1 className="mt-3 text-2xl font-semibold text-(--text-primary)">Citizen help</h1>
        <p className="mt-1 max-w-2xl text-sm text-(--text-muted)">
          Safety guidance and incident reporting. <strong className="text-(--text-primary)">If you or someone else is in immediate danger, call your local emergency number first.</strong>
        </p>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section className="glass-panel flex h-[28rem] flex-col p-5" aria-label="Safety assistant">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-(--text-primary)">Safety assistant</h2>
              <select aria-label="Language" value={language} onChange={(e) => setLanguage(e.target.value)} className="rounded-md border border-(--border) bg-white/5 px-2 py-1 text-xs text-(--text-primary)">
                {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
            </div>
            <div className="mt-3 flex-1 space-y-2 overflow-y-auto pr-1" aria-live="polite">
              {messages.length === 0 && (
                <p className="text-xs text-(--text-muted)">Ask about evacuation, shelters, first aid or what to do during a flood or cyclone. Answers come from official guidance; if none applies, the assistant says so.</p>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${m.role === "you" ? "ml-auto bg-(--accent)/20 text-(--text-primary)" : "bg-white/5 text-(--text-primary)"}`}>
                  {m.text}
                  {m.note && <p className="mt-1 text-[11px] text-(--text-muted)">{m.note}</p>}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
            <form onSubmit={send} className="mt-3 flex gap-2">
              <input value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={1000} placeholder="Type your question" className={input} aria-label="Your question" />
              <button disabled={sending} className="cursor-pointer rounded-md border border-(--accent) bg-(--accent)/20 px-4 text-sm disabled:opacity-50">
                {sending ? "…" : "Send"}
              </button>
            </form>
          </section>

          <section className="glass-panel p-5" aria-label="Report an incident">
            <h2 className="text-sm font-semibold text-(--text-primary)">Report an incident</h2>
            <p className="mt-1 text-xs text-(--text-muted)">Reports are checked against sensor data before anyone acts on them. Your device location is attached only if you allow it.</p>
            {reportState === "sent" ? (
              <p className="mt-4 rounded-md border border-(--border) bg-white/5 p-3 text-sm text-(--text-primary)">Thank you — your report was received and will be reviewed by the response team.</p>
            ) : (
              <form onSubmit={report} className="mt-4 flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
                  What is happening?
                  <textarea required value={reportText} onChange={(e) => setReportText(e.target.value)} maxLength={2000} rows={4} className={input} />
                </label>
                <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
                  How severe is it? ({Math.round(severity * 100)}%)
                  <input type="range" min={0} max={1} step={0.1} value={severity} onChange={(e) => setSeverity(Number(e.target.value))} />
                </label>
                <label className="flex flex-col gap-1 text-xs text-(--text-muted)">
                  Contact (optional)
                  <input value={contact} onChange={(e) => setContact(e.target.value)} maxLength={200} className={input} autoComplete="tel" />
                </label>
                {reportState === "error" && (
                  <p role="alert" className="text-xs text-(--sev-critical)">
                    {limited ? "Too many reports from this connection — please wait a minute." : "Couldn't send the report. Please try again, or call local emergency services."}
                  </p>
                )}
                <button disabled={reportState === "sending"} className="cursor-pointer rounded-md border border-(--accent) bg-(--accent)/20 py-2 text-sm disabled:opacity-50">
                  {reportState === "sending" ? "Sending…" : "Send report"}
                </button>
              </form>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
