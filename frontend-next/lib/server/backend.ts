import "server-only";

// Server-side helpers for the same-origin proxy routes under app/api/*.
// Device credentials live in server env only (never NEXT_PUBLIC_*), so they
// are not shipped to browsers.

export const BACKEND_URL = (
  process.env.BACKEND_URL ??
  process.env.NEXT_PUBLIC_API_BASE ??
  "http://localhost:8001"
).replace(/\/+$/, "");

export function deviceHeaders(prefix: "CITIZEN" | "DEMO_IOT"): Record<string, string> | null {
  const id = process.env[`${prefix}_DEVICE_ID`] ?? (prefix === "CITIZEN" ? "citizen-default" : "iot-default");
  const secret = process.env[`${prefix}_DEVICE_SECRET`];
  if (!secret) return null;
  return { "X-Device-Id": id, "X-Device-Secret": secret };
}

export function clientIp(request: Request): string {
  const fwd = request.headers.get("x-forwarded-for");
  return (fwd ? fwd.split(",")[0].trim() : request.headers.get("x-real-ip")) || "unknown";
}

// Best-effort per-instance sliding-window limiter. It blunts abuse of the
// public citizen endpoints; for multi-instance deployments put a shared
// limiter (CDN / gateway) in front as well.
const hits = new Map<string, number[]>();

export function rateLimited(key: string, limit: number, windowMs = 60_000): boolean {
  const now = Date.now();
  const recent = (hits.get(key) ?? []).filter((t) => now - t < windowMs);
  if (recent.length >= limit) {
    hits.set(key, recent);
    return true;
  }
  recent.push(now);
  hits.set(key, recent);
  if (hits.size > 5000) {
    for (const [k, v] of hits) if (!v.some((t) => now - t < windowMs)) hits.delete(k);
  }
  return false;
}

export function json(body: unknown, status = 200): Response {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } });
}

export async function readJson(request: Request, maxBytes = 8_192): Promise<Record<string, unknown> | null> {
  const text = await request.text();
  if (text.length > maxBytes) return null;
  try {
    const value = JSON.parse(text);
    return value && typeof value === "object" && !Array.isArray(value) ? value : null;
  } catch {
    return null;
  }
}
