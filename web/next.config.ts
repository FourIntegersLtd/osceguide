import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs/config";
import path from "node:path";
import { fileURLToPath } from "node:url";

const platformRoot = path.dirname(fileURLToPath(import.meta.url));
const platformNodeModules = path.join(platformRoot, "node_modules");
/** Turbopack only resolves files under `turbopack.root`; aliases are relative to it. */
const repoRoot = path.join(platformRoot, "..");

/**
 * Turbopack does not always apply tsconfig `paths`, so `@/` → `src/` is spelled
 * out here as well. There used to be two more entries pointing at
 * `frontend/src/b2b` and `frontend/src/shared`; the template builder and the
 * station structures they served are ported into
 * `capabilities/authoring/structure` now, so this project builds with the old
 * tree deleted.
 */
const turbopackAliases = {
  "@": "web/src",
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
    // The /api/v1 rewrite gives up after 30 s by default, and drafting a slide deck takes longer:
    // the API finished, but the browser got a 500 and nothing was saved.
    proxyTimeout: 300_000,
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
    resolveAlias: turbopackAliases,
  },
  webpack: (config) => {
    config.resolve.modules = [
      platformNodeModules,
      ...(config.resolve.modules ?? ["node_modules"]),
    ];
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
          // Deny the powerful browser features this app never uses. Camera and
          // microphone stay allowed to self because the LiveKit voice station
          // needs them; everything else is switched off so a compromised or
          // injected script cannot reach for it. A full Content-Security-Policy
          // is deliberately not set here — it must be validated in a browser on
          // staging first (see docs/security), since a wrong CSP breaks the app
          // silently.
          {
            key: "Permissions-Policy",
            value:
              "geolocation=(), payment=(), usb=(), camera=(self), microphone=(self), fullscreen=(self)",
          },
        ],
      },
      // A cached worker script would pin every installed app to an old one.
      {
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
        ],
      },
    ];
  },
};

/**
 * Error reporting (E-13). The runtime side is `src/instrumentation*.ts` and is
 * off without a DSN. This wrapper only matters at build time: with
 * `SENTRY_AUTH_TOKEN` (plus `SENTRY_ORG`/`SENTRY_PROJECT`) it uploads source
 * maps so stack traces read as source; without one it uploads nothing and
 * says nothing, which is every local and CI build.
 */
export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: !process.env.SENTRY_AUTH_TOKEN,
  telemetry: false,
  sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
});
