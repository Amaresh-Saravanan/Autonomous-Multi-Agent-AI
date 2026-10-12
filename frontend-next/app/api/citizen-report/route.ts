import { BACKEND_URL, clientIp, deviceHeaders, json, rateLimited, readJson } from "@/lib/server/backend";

// Public citizen incident report (PRD SEC-4: reports are trust-scored by the
// backend, never auto-acted on). Only the incident id is echoed back.
export async function POST(request: Request) {
  if (rateLimited(`report:${clientIp(request)}`, 5)) return json({ error: "rate_limited" }, 429);

  const body = await readJson(request);
  const message = typeof body?.message === "string" ? body.message.trim() : "";
  const severity = Number(body?.claimed_severity ?? 0.5);
  const lat = body?.lat === undefined || body.lat === null ? undefined : Number(body.lat);
  const lon = body?.lon === undefined || body.lon === null ? undefined : Number(body.lon);
  const contact = typeof body?.reporter_contact === "string" ? body.reporter_contact.trim().slice(0, 200) : undefined;

  const coordsOk =
    (lat === undefined && lon === undefined) ||
    (lat !== undefined && lon !== undefined && Math.abs(lat) <= 90 && Math.abs(lon) <= 180);
  if (!message || message.length > 2000 || !(severity >= 0 && severity <= 1) || !coordsOk) {
    return json({ error: "invalid_request" }, 400);
  }

  const headers = deviceHeaders("CITIZEN");
  if (!headers) return json({ error: "citizen_reports_not_configured" }, 503);

  try {
    const upstream = await fetch(`${BACKEND_URL}/api/v1/ingestion/citizen`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({
        message,
        claimed_severity: severity,
        lat,
        lon,
        reporter_contact: contact || undefined,
      }),
      signal: AbortSignal.timeout(20_000),
    });
    if (!upstream.ok) return json({ error: "upstream_error" }, 502);
    const accepted = await upstream.json();
    return json({ incident_id: accepted.incident_id }, 202);
  } catch {
    return json({ error: "upstream_unreachable" }, 502);
  }
}
