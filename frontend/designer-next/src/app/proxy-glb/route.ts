import { type NextRequest, NextResponse } from "next/server";

const ALLOWED_HOSTS = [
  ".ikea.com",
  ".fal.ai",
  ".fal.run",
  ".sketchfab.com",
  ".poly.pizza",
  ".digitaloceanspaces.com",
];

export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url");
  if (!url || !url.startsWith("https://")) {
    return NextResponse.json({ error: "Only HTTPS URLs allowed" }, { status: 400 });
  }

  const hostname = new URL(url).hostname;
  if (!ALLOWED_HOSTS.some((h) => hostname.endsWith(h))) {
    return NextResponse.json({ error: "Domain not allowed" }, { status: 403 });
  }

  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      return NextResponse.json({ error: `Upstream ${resp.status}` }, { status: 502 });
    }

    return new Response(resp.body, {
      headers: {
        "Content-Type": resp.headers.get("content-type") ?? "model/gltf-binary",
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (e) {
    return NextResponse.json({ error: `Fetch failed: ${e}` }, { status: 502 });
  }
}
