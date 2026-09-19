import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  trailingSlash: false,
  // Local subdomain testing: <exam>.lvh.me resolves to 127.0.0.1.
  allowedDevOrigins:
    process.env.NODE_ENV === "development" ? ["lvh.me", "*.lvh.me"] : undefined,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
