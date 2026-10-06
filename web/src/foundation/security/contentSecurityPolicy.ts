/**
 * SEC-006: a Content-Security-Policy for the web app.
 *
 * The point of this header is to *contain* an XSS: even if a script sink were
 * reintroduced (SEC-002 was one), an injected inline `<script>` cannot run,
 * because only scripts carrying this request's nonce — or scripts those load,
 * via `strict-dynamic` — are allowed to execute. That is the control the app
 * shipped without.
 *
 * A Next.js CSP has to be built per request, not in `next.config.ts`'s static
 * `headers()`, because each response needs its own random nonce and Next reads
 * that nonce off the request's `Content-Security-Policy` header to stamp its own
 * bootstrap scripts. So the middleware mints the nonce, forwards it on the
 * request, and sets the response header — this module builds the string both
 * sides share, and is unit-tested so the directives cannot silently drift.
 *
 * **It ships in `Report-Only` mode unless `PLATFORM_WEB_CSP_ENFORCE` is set.**
 * A wrong CSP breaks the app silently (a blocked chunk is a blank page with a
 * console error), so the safe rollout — the one the security report prescribes —
 * is to report violations from staging through the whole journey (sign-in,
 * attempt, voice, debrief), tune, and only then enforce by setting the flag.
 */

export interface CspHeader {
  /** `Content-Security-Policy` when enforcing, `-Report-Only` otherwise. */
  readonly name: "Content-Security-Policy" | "Content-Security-Policy-Report-Only";
  /** The policy string, carrying this request's nonce. */
  readonly value: string;
  /** The nonce, forwarded on the request so Next can stamp its own scripts. */
  readonly nonce: string;
  /** Whether the policy is enforced (blocks) or report-only (observes). */
  readonly enforce: boolean;
}

/** A fresh base64 nonce from the platform CSPRNG (Web Crypto; present in Edge and Node). */
export function generateNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

/**
 * The policy string for one request.
 *
 * `connect-src` and `img-src` are deliberately broad (`https:`, `wss:`): the app
 * talks to LiveKit Cloud websockets on a per-session address, S3 for images and,
 * where configured, analytics — none on a fixed host. The XSS-containment win is
 * `script-src` (nonce + `strict-dynamic`, no `unsafe-inline`); the other
 * directives are tightened from violation reports once enforcing.
 */
export function contentSecurityPolicyValue(nonce: string, options: { isDev: boolean; enforce: boolean }): string {
  const scriptSrc = [
    "'self'",
    `'nonce-${nonce}'`,
    // Lets Next's nonced loader pull the chunks it needs without listing each.
    "'strict-dynamic'",
    // Dev-only: Next's HMR/runtime uses eval. Never emitted in a production build.
    options.isDev ? "'unsafe-eval'" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const directives: Array<[string, string]> = [
    ["default-src", "'self'"],
    ["script-src", scriptSrc],
    // React/Next inject inline styles; nonce-ing every one is impractical and
    // style injection is low-risk next to script execution.
    ["style-src", "'self' 'unsafe-inline'"],
    ["img-src", "'self' data: blob: https:"],
    ["font-src", "'self' data:"],
    ["connect-src", "'self' https: wss:"],
    ["media-src", "'self' blob: data:"],
    ["worker-src", "'self' blob:"],
    ["object-src", "'none'"],
    ["base-uri", "'self'"],
    ["form-action", "'self'"],
    // The enforcing twin of the X-Frame-Options: DENY already set.
    ["frame-ancestors", "'none'"],
  ];

  const parts = directives.map(([name, value]) => `${name} ${value}`);
  // Only meaningful over HTTPS, so never in dev; and browsers ignore it (with a
  // console error on every page) in a Report-Only policy, so only when enforcing.
  if (!options.isDev && options.enforce) parts.push("upgrade-insecure-requests");
  return parts.join("; ");
}

/**
 * The full header for this request: a fresh nonce, the policy, and whether it
 * enforces. `enforce` defaults off (report-only) — see the module note.
 */
export function buildCspHeader(options: { isDev: boolean; enforce: boolean }): CspHeader {
  const nonce = generateNonce();
  return {
    name: options.enforce ? "Content-Security-Policy" : "Content-Security-Policy-Report-Only",
    value: contentSecurityPolicyValue(nonce, options),
    nonce,
    enforce: options.enforce,
  };
}

/** `PLATFORM_WEB_CSP_ENFORCE` truthy → enforce; anything else → report-only. */
export function cspEnforceFromEnv(value: string | undefined): boolean {
  if (!value) return false;
  return ["1", "true", "yes", "on", "enforce"].includes(value.trim().toLowerCase());
}
