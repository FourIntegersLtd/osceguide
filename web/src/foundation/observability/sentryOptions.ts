import { IS_PRODUCTION_SITE, SITE_HOSTNAME } from "@/foundation/config/siteUrl";

/**
 * Error reporting settings, shared by the browser, server and edge runtimes.
 *
 * Off unless a DSN is set, as in platform-api (`core/observability.py`): local
 * and test runs stay silent, and a deployment opts in by configuration rather
 * than by code. The browser reads `NEXT_PUBLIC_SENTRY_DSN`, which is inlined
 * at build time; a DSN is a public write-only key, so shipping it is how every
 * browser SDK works. The server may use its own `SENTRY_DSN`.
 */

/**
 * Traces are sampled, not all sent. Same rate as platform-api: the supervisor
 * console polls, and every poll would otherwise be a billed transaction.
 */
export const TRACES_SAMPLE_RATE = 0.05;

export type SentryRuntime = "client" | "server";

export interface SentryOptions {
  dsn: string;
  environment: string;
  tracesSampleRate: number;
  sendDefaultPii: false;
}

/** The deployment's name, as platform-api's `APP_ENV` names it. */
export function sentryEnvironment(env: Record<string, string | undefined>): string {
  const explicit = env.NEXT_PUBLIC_SENTRY_ENVIRONMENT?.trim();
  if (explicit) return explicit;
  // Staging and previews build with NODE_ENV=production too, so the site URL is
  // what tells them apart (see foundation/config/siteUrl.ts).
  if (IS_PRODUCTION_SITE) return "production";
  return SITE_HOSTNAME.startsWith("localhost") || SITE_HOSTNAME.startsWith("127.")
    ? "local"
    : "staging";
}

/** What to start Sentry with, or `null` to leave it off. */
export function sentryOptions(
  runtime: SentryRuntime,
  env: Record<string, string | undefined>,
): SentryOptions | null {
  const dsn = (
    runtime === "server" ? env.SENTRY_DSN || env.NEXT_PUBLIC_SENTRY_DSN : env.NEXT_PUBLIC_SENTRY_DSN
  )?.trim();
  if (!dsn) return null;
  return {
    dsn,
    environment: sentryEnvironment(env),
    tracesSampleRate: TRACES_SAMPLE_RATE,
    // Request bodies here hold passwords, recovery codes and transcripts, and
    // the headers hold the access token. None of that belongs in a report.
    sendDefaultPii: false,
  };
}

/**
 * Strip what a report must never carry, whatever the SDK collected.
 *
 * `sendDefaultPii: false` already drops cookies and the user's IP; this is
 * the belt to those braces for the request itself, since one leaked bearer
 * token in an error report is a session in somebody else's hands.
 */
export function scrubEvent<
  T extends { request?: { headers?: Record<string, string>; cookies?: unknown; data?: unknown } },
>(event: T): T {
  if (!event.request) return event;
  const headers = { ...(event.request.headers ?? {}) };
  for (const name of Object.keys(headers)) {
    if (/^(authorization|cookie|x-api-key)$/i.test(name)) delete headers[name];
  }
  return { ...event, request: { ...event.request, headers, cookies: undefined, data: undefined } };
}
