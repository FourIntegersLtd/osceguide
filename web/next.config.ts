import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const platformRoot = path.dirname(fileURLToPath(import.meta.url));
const platformNodeModules = path.join(platformRoot, "node_modules");
/** Turbopack only resolves files under `turbopack.root`; aliases are relative to it. */
const repoRoot = path.join(platformRoot, "..");
const b2bRoot = path.join(repoRoot, "frontend/src/b2b");
const sharedRoot = path.join(repoRoot, "frontend/src/shared");

/** Must beat `@/*` → `./src/*`, which would wrongly resolve `@/b2b/...` to `src/b2b/...`. */
const b2bAliases = {
  "@/b2b": b2bRoot,
  "@/shared": sharedRoot,
} as const;

/** Paths are relative to `turbopack.root` (repo root), not `platform-web/`. */
const turbopackB2bAliases = {
  "@/b2b": "frontend/src/b2b",
  "@/shared": "frontend/src/shared",
  // Turbopack does not always apply tsconfig `paths`; keep `@/` → `src/` explicit.
  "@": "platform-web/src",
} as const;

const DEFAULT_PLATFORM_API = "http://127.0.0.1:8002";

function resolvePlatformApiOrigin(): string {
  const raw = process.env.PLATFORM_API_URL?.replace(/\/+$/, "");
  if (!raw) return DEFAULT_PLATFORM_API;
  // A common mis-set: point the proxy at Next (:3000/:3100) instead of platform-api (:8002).
  if (/:(3000|3100)(\/|$)/.test(raw)) {
    console.warn(
      `[platform-web] PLATFORM_API_URL (${raw}) is the frontend dev server, not platform-api — using ${DEFAULT_PLATFORM_API}`,
    );
    return DEFAULT_PLATFORM_API;
  }
  return raw;
}

const platformApiOrigin = resolvePlatformApiOrigin();

const nextConfig: NextConfig = {
  trailingSlash: false,
  experimental: {
    externalDir: true,
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*",
          destination: `${platformApiOrigin}/api/v1/:path*`,
        },
      ],
    };
  },
  turbopack: {
    root: repoRoot,
    resolveAlias: turbopackB2bAliases,
  },
  webpack: (config) => {
    config.resolve.modules = [
      platformNodeModules,
      ...(config.resolve.modules ?? ["node_modules"]),
    ];
    config.resolve.alias = {
      ...config.resolve.alias,
      ...b2bAliases,
    };
    return config;
  },
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
