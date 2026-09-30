import * as Sentry from "@sentry/nextjs";
import { scrubEvent, sentryOptions } from "@/foundation/observability/sentryOptions";

/**
 * Browser error reporting (E-13), started before the app is interactive.
 *
 * `process.env.NEXT_PUBLIC_*` must be read by name for Next to inline it, so
 * the object is spelled out rather than passing `process.env`.
 */
const options = sentryOptions("client", {
  NEXT_PUBLIC_SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN,
  NEXT_PUBLIC_SENTRY_ENVIRONMENT: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT,
});

if (options) {
  Sentry.init({ ...options, beforeSend: (event) => scrubEvent(event) });
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
