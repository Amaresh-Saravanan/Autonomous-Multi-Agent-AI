import { BACKEND_URL, clientIp, deviceHeaders, json, rateLimited, readJson } from "@/lib/server/backend";

// Public "request an account" form (SEC-1: an admin approves every account).
// The backend always answers with the same acknowledgement, so this route
// does too — it never reveals whether an email already has an account.
const ROLES = new Set(["OPERATOR", "VIEWER"]);
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: Request) {
  if (rateLimited(`access:${clientIp(request)}`, 5, 15 * 60_000)) return json({ error: "rate_limited" }, 429);

  const body = await readJson(request);
  const email = typeof body?.email === "string" ? body.email.trim() : "";
  const fullName = typeof body?.full_name === "string" ? body.full_name.trim() : "";
  const agency = typeof body?.agency_text === "string" ? body.agency_text.trim() : "";
  const role = typeof body?.requested_role === "string" ? body.requested_role : undefined;
  if (!EMAIL.test(email) || email.length > 254 || fullName.length < 2 || fullName.length > 200 || agency.length > 200 || (role && !ROLES.has(role))) {
    return json({ error: "invalid_request" }, 400);
  }

  const headers = deviceHeaders("CITIZEN");
  if (!headers) return json({ error: "not_configured" }, 503);
  try {
    const upstream = await fetch(`${BACKEND_URL}/api/v1/access/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({ email, full_name: fullName, agency_text: agency || undefined, requested_role: role }),
      signal: AbortSignal.timeout(15_000),
    });
    if (!upstream.ok) return json({ error: "upstream_error" }, 502);
    return json({ status: "received" }, 202);
  } catch {
    return json({ error: "upstream_unreachable" }, 502);
  }
}
