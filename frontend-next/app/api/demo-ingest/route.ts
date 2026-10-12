import { NextRequest, NextResponse } from "next/server";

// Server-side proxy for the "simulate a sensor" demo button. Device
// credentials are read from non-public env vars here (never NEXT_PUBLIC_*,
// which would ship them to every visitor's browser bundle) and attached
// to the real backend call.
const API_BASE = process.env.API_BASE ?? "http://localhost:8001";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await fetch(`${API_BASE}/api/v1/ingestion/iot`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Device-Id": process.env.DEMO_DEVICE_ID ?? "",
      "X-Device-Secret": process.env.DEMO_DEVICE_SECRET ?? "",
    },
    body,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
