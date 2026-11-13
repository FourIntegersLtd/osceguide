import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  buildCspHeader,
  contentSecurityPolicyValue,
  cspEnforceFromEnv,
  generateNonce,
} from "@/foundation/security/contentSecurityPolicy";

/**
 * SEC-006 regression: the Content-Security-Policy must actually contain a script
 * injection, and must not weaken itself on the way there.
 *
 * The failure this guards is silent in both directions. Drop `'nonce-…'` or
 * `'strict-dynamic'` and the app stops loading (a blocked chunk is a blank
 * page); slip `'unsafe-inline'` into `script-src` and the header is present, the
 * scanner is satisfied, and every injected `<script>` runs anyway — the exact
 * control the report said was missing.
 */
describe("content-security-policy", () => {
  it("binds script execution to a per-request nonce, never to unsafe-inline", () => {
    const nonce = generateNonce();
    const value = contentSecurityPolicyValue(nonce, { isDev: false, enforce: true });

    const scriptSrc = directive(value, "script-src");
    assert.match(scriptSrc, new RegExp(`'nonce-${escapeForRegExp(nonce)}'`));
    assert.ok(scriptSrc.includes("'strict-dynamic'"), "strict-dynamic loads the nonced chunks");
    assert.ok(
      !scriptSrc.includes("'unsafe-inline'"),
      "unsafe-inline would let any injected inline script run",
    );
    assert.ok(!scriptSrc.includes("'unsafe-eval'"), "no eval in a production policy");
    assert.ok(scriptSrc.includes("'wasm-unsafe-eval'"), "the non-verbal face model compiles WebAssembly");
  });

  it("locks down the framing and object vectors X-Frame-Options only half-covered", () => {
    const value = contentSecurityPolicyValue(generateNonce(), { isDev: false, enforce: true });
    assert.equal(directive(value, "frame-ancestors"), "'none'");
    assert.equal(directive(value, "object-src"), "'none'");
    assert.equal(directive(value, "base-uri"), "'self'");
    assert.equal(directive(value, "default-src"), "'self'");
  });

  it("keeps the app's real backends reachable so enforcing does not black out the page", () => {
    const value = contentSecurityPolicyValue(generateNonce(), { isDev: false, enforce: true });
    // LiveKit Cloud websockets and https APIs (S3 images, analytics) are on
    // per-session or per-tenant hosts, so these stay scheme-broad by design.
    assert.ok(directive(value, "connect-src").includes("wss:"), "LiveKit needs websockets");
    assert.ok(directive(value, "connect-src").includes("https:"));
    assert.ok(directive(value, "img-src").includes("https:"), "S3-hosted images");
    for (const host of ["https://d1wmb89lczbkpf.cloudfront.net", "https://osceguide-platform.s3.eu-west-2.amazonaws.com"]) {
      assert.ok(directive(value, "media-src").includes(host), `media-src must allow ${host}`);
    }
  });

  it("only allows eval, and only upgrades insecure requests, where each is right", () => {
    const dev = contentSecurityPolicyValue("n", { isDev: true, enforce: true });
    const prod = contentSecurityPolicyValue("n", { isDev: false, enforce: true });

    // React's dev runtime needs eval; a production build never does.
    assert.ok(directive(dev, "script-src").includes("'unsafe-eval'"));
    assert.ok(!directive(prod, "script-src").includes("'unsafe-eval'"));

    // upgrade-insecure-requests is meaningful over HTTPS (production), not on
    // plain-HTTP localhost, where it would rewrite dev requests to nowhere.
    assert.ok(prod.includes("upgrade-insecure-requests"));
    assert.ok(!dev.includes("upgrade-insecure-requests"));
  });

  it("leaves upgrade-insecure-requests out of a Report-Only policy, where browsers ignore it", () => {
    // Every page on staging logged "'upgrade-insecure-requests' is ignored when
    // delivered in a report-only policy" (B56), failing every verify run.
    const reportOnly = buildCspHeader({ isDev: false, enforce: false });
    assert.equal(reportOnly.name, "Content-Security-Policy-Report-Only");
    assert.ok(!reportOnly.value.includes("upgrade-insecure-requests"));

    const enforced = buildCspHeader({ isDev: false, enforce: true });
    assert.ok(enforced.value.split("; ").includes("upgrade-insecure-requests"));
  });

  it("ships Report-Only until the enforce flag is explicitly set", () => {
    const off = buildCspHeader({ isDev: false, enforce: false });
    assert.equal(off.name, "Content-Security-Policy-Report-Only");
    assert.equal(off.enforce, false);

    const on = buildCspHeader({ isDev: false, enforce: true });
    assert.equal(on.name, "Content-Security-Policy");
    assert.equal(on.enforce, true);

    // The nonce in the header value is the one the caller forwards to Next.
    assert.ok(on.value.includes(`'nonce-${on.nonce}'`));
  });

  it("reads the enforce flag conservatively — truthy strings only, default off", () => {
    for (const truthy of ["1", "true", "TRUE", "yes", "on", "enforce"]) {
      assert.equal(cspEnforceFromEnv(truthy), true, `${truthy} should enforce`);
    }
    for (const falsy of [undefined, "", "0", "false", "no", "report-only", "off"]) {
      assert.equal(cspEnforceFromEnv(falsy), false, `${String(falsy)} should stay report-only`);
    }
  });

  it("mints an unpredictable, unique nonce each call", () => {
    const seen = new Set<string>();
    for (let i = 0; i < 100; i += 1) {
      const nonce = generateNonce();
      assert.ok(nonce.length >= 16, "a guessable nonce defeats the whole control");
      assert.ok(!seen.has(nonce), "nonces must not repeat");
      seen.add(nonce);
    }
  });
});

/** The value of one directive, e.g. `directive(csp, "script-src")` → `"'self' 'nonce-…'"`. */
function directive(policy: string, name: string): string {
  const found = policy
    .split(";")
    .map((part) => part.trim())
    .find((part) => part === name || part.startsWith(`${name} `));
  assert.ok(found !== undefined, `policy is missing a ${name} directive: ${policy}`);
  return found.slice(name.length).trim();
}

function escapeForRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");
}
