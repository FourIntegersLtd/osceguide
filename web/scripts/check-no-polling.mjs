// Does any screen poll? The standing rule: no polling, screens wait on SSE (`useMeEvents`).
// A timer may change display copy; it may never call the api.
//
// A non-test source file fails if it contains
//   - `setInterval(`, or
//   - a `setTimeout(` whose callback (the next 400 characters) calls `fetch(`, calls a function
//     imported from a module whose path contains "/api" or "platform", or calls the function the
//     `setTimeout` sits in (a self-rescheduling loop).
//
// Allow-lists only shrink: ALLOW carries its own ceiling, and an entry nothing needs fails.
//
// Usage: node scripts/check-no-polling.mjs

import { fileURLToPath } from "node:url";
import { allowList, finish, read, rel, sourceFiles } from "./lib-src.mjs";

const WINDOW = 400;

// file (relative to web/) -> why a timer there is not polling
const ALLOW = allowList(
  {
    // 1 s / 30 s display clocks and rotations: they set state, they read nothing
    "src/capabilities/account/AuthQuotePanel.tsx": "testimonial rotation, display only",
    "src/capabilities/attempt-runner/ExamClock.tsx": "display tick between server readings of remaining_seconds",
    "src/capabilities/attempt-runner/useCountdown.ts": "display tick against the server deadline",
    "src/capabilities/peer-practice/PeerPracticeProvider.tsx": "30 s display clock for the join window",
    "src/capabilities/peer-practice/marketplace/UpcomingSessions.tsx": "30 s display clock for the join window",
    "src/capabilities/peer-practice/queue/MatchNotificationModal.tsx": "1 s countdown to the accept deadline; the one auto-decline at zero is a single call, not a loop",
    "src/capabilities/peer-practice/support/usePeerSession.ts": "1 s display clock; the single-shot reloads at the server's phase deadline are not a loop",
    "src/domains/marketing/home/HeroPhrase.tsx": "public page phrase rotation, display only",
    "src/foundation/ui/Timer.tsx": "display tick against the server deadline",
    // false positives: a timer within 400 characters of an api call that it does not make
    "src/capabilities/authoring/rubrics/useSchemeDraft.ts": "typing debounce: one preview after a pause, not a loop",
    "src/capabilities/media/useJumpIndex.ts": "scroll lock release, no api",
    "src/capabilities/onboarding/useOnboardingVoice.ts": "one-off wait for the mic prompt before starting the session",
    "src/domains/platform/ReferralPayouts.tsx": "clears the 'copied' label after 2 s",
    // a retry, not a poll
    "src/foundation/hooks/useEventStream.ts": "EventSource reconnect backoff: reopens the stream, reads no state",
    "src/foundation/session/SessionProvider.tsx": "capped exponential backoff after a failed session check, stops on success",
    // KNOWN POLLING outside Lane E: replace with an SSE wait, then delete this entry
    "src/capabilities/account/PaymentReturn.tsx": "KNOWN POLLING: confirmPayment sleeps and re-reads receipts after Stripe returns; owner access-owner to move to SSE",
  },
  16,
);

/** Names this file imports from a module path containing "/api" or "platform". */
export function apiImports(src) {
  const names = new Set();
  const re = /import\s+(?:type\s+)?(?:([\w$]+)\s*,?\s*)?(?:\{([^}]*)\}|\*\s+as\s+([\w$]+))?\s*from\s*["']([^"']+)["']/g;
  for (const m of src.matchAll(re)) {
    if (!/\/api|platform/.test(m[4])) continue;
    if (m[1]) names.add(m[1]);
    if (m[3]) names.add(m[3]);
    for (const part of (m[2] ?? "").split(",")) {
      const name = part.replace(/^\s*type\s+/, "").split(/\s+as\s+/).pop().trim();
      if (name) names.add(name);
    }
  }
  return names;
}

/** The name of the function a `setTimeout(` at `index` sits in, or null. */
function enclosingFunction(src, index) {
  const before = src.slice(0, index);
  const decl = [
    ...before.matchAll(
      /(?:function\s+([\w$]+)|(?:const|let)\s+([\w$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w$]+)\s*(?::[^=]+)?=>)/g,
    ),
  ];
  const last = decl.at(-1);
  return last ? (last[1] ?? last[2]) : null;
}

const callsName = (text, name) => new RegExp(`(?<![\\w$.])${name.replace(/\$/g, "\\$")}\\s*\\(`).test(text);

/** The reasons `src` polls, one string each. */
export function pollingHits(src) {
  const hits = [];
  if (/\bsetInterval\s*\(/.test(src)) hits.push("setInterval(");
  const imported = apiImports(src);
  for (const m of src.matchAll(/\bsetTimeout\s*\(/g)) {
    const body = src.slice(m.index + m[0].length, m.index + m[0].length + WINDOW);
    if (/\bfetch\s*\(/.test(body)) hits.push("setTimeout( that calls fetch(");
    for (const name of imported) if (callsName(body, name)) hits.push(`setTimeout( that calls ${name}() from an api module`);
    const outer = enclosingFunction(src, m.index);
    if (outer && callsName(body, outer)) hits.push(`setTimeout( that re-calls ${outer}()`);
  }
  return hits;
}

// Run only as a script, so the test can import pollingHits.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const offenders = [];
  for (const f of sourceFiles()) {
    const hits = pollingHits(read(f));
    if (hits.length === 0 || ALLOW.has(rel(f))) continue;
    offenders.push(`${rel(f)}: ${[...new Set(hits)].join("; ")}`);
  }
  finish("check-no-polling", offenders, ALLOW);
}
