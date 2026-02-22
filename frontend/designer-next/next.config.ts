import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:8100/api/:path*" },
      { source: "/voice_intake/:path*", destination: "http://localhost:8100/voice_intake/:path*" },
      { source: "/backend-session/:path*", destination: "http://localhost:8100/session/:path*" },
      { source: "/voice/:path*", destination: "http://localhost:8100/voice/:path*" },
      { source: "/tool/:path*", destination: "http://localhost:8100/tool/:path*" },
    ];
  },
};

export default nextConfig;
