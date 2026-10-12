import { BACKEND_URL, clientIp, deviceHeaders, json, rateLimited, readJson } from "@/lib/server/backend";

// Public "forgot password" form. Always acknowledges identically (the backend
// only queues a request when the account exists); an admin issues the
// temporary password.
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: Request) {
  if (rateLimited(`reset:${clientIp(request)}`, 5, 15 * 60_000)) return json({ error: "rate_limited" }, 429);

  const body = await readJson(request);
  const email = typeof body?.email === "string" ? body.email.trim() : "";
  if (!EMAIL.test(email) || email.length > 254) return json({ error: "invalid_request" }, 400);

  const headers = deviceHeaders("CITIZEN");
  if (!headers) return json({ error: "not_configured" }, 503);
  try {
    const upstream = await fetch(`${BACKEND_URL}/api/v1/access/reset-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ email }),
      signal: AbortSignal.timeout(15_000),
    });
    if (!upstream.ok) return json({ error: "upstream_error" }, 502);
    return json({ status: "received" }, 202);
  } catch {
    return json({ error: "upstream_unreachable" }, 502);
  }
}
