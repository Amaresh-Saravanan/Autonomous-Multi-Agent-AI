import { BACKEND_URL, clientIp, deviceHeaders, json, rateLimited, readJson } from "@/lib/server/backend";

// Public citizen assistant (PRD UI-6 / AG-7). The browser talks to this
// route; this route adds the citizen device credential server-side.
const LANGUAGES = new Set(["en", "hi", "ta", "te", "bn", "mr"]);

export async function POST(request: Request) {
  if (rateLimited(`chat:${clientIp(request)}`, 20)) return json({ error: "rate_limited" }, 429);

  const body = await readJson(request);
  const message = typeof body?.message === "string" ? body.message.trim() : "";
  const language = typeof body?.language === "string" ? body.language : "en";
  if (!message || message.length > 1000 || !LANGUAGES.has(language)) {
    return json({ error: "invalid_request" }, 400);
  }

  const headers = deviceHeaders("CITIZEN");
  if (!headers) return json({ error: "citizen_assistant_not_configured" }, 503);

  try {
    const upstream = await fetch(`${BACKEND_URL}/api/v1/citizen/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ message, language }),
      signal: AbortSignal.timeout(20_000),
    });
    if (!upstream.ok) return json({ error: "upstream_error" }, upstream.status === 429 ? 429 : 502);
    return json(await upstream.json());
  } catch {
    return json({ error: "upstream_unreachable" }, 502);
  }
}
