import { BACKEND_URL, deviceHeaders, json, readJson } from "@/lib/server/backend";

// Demo "simulate a sensor" button. Off unless DEMO_INGEST_ENABLED=true, and
// even then only an authenticated OPERATOR/ADMIN may use it — the caller's
// bearer token is verified against the backend before the (server-held)
// sensor credential is used. Never enable in a real production deployment.
export async function POST(request: Request) {
  if (process.env.DEMO_INGEST_ENABLED !== "true") return json({ error: "not_found" }, 404);

  const auth = request.headers.get("authorization");
  if (!auth?.startsWith("Bearer ")) return json({ error: "unauthorized" }, 401);

  const me = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
    headers: { Authorization: auth },
    signal: AbortSignal.timeout(10_000),
  }).catch(() => null);
  if (!me || !me.ok) return json({ error: "unauthorized" }, 401);
  const { role } = await me.json();
  if (role !== "OPERATOR" && role !== "ADMIN") return json({ error: "forbidden" }, 403);

  const body = await readJson(request);
  const reading = Number(body?.reading);
  if (!Number.isFinite(reading) || reading < 0 || reading > 100) return json({ error: "invalid_request" }, 400);

  const headers = deviceHeaders("DEMO_IOT");
  if (!headers) return json({ error: "demo_sensor_not_configured" }, 503);

  try {
    const upstream = await fetch(`${BACKEND_URL}/api/v1/ingestion/iot`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...headers },
      body: JSON.stringify({
        sensor_id: "wl-042",
        metric: "water_level",
        reading,
        unit: "m",
        lat: 13.0827,
        lon: 80.2707,
      }),
      signal: AbortSignal.timeout(20_000),
    });
    if (!upstream.ok) return json({ error: "upstream_error" }, 502);
    return json(await upstream.json(), 202);
  } catch {
    return json({ error: "upstream_unreachable" }, 502);
  }
}
