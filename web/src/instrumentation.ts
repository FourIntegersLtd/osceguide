import * as Sentry from "@sentry/nextjs";
import { scrubEvent, sentryOptions } from "@/foundation/observability/sentryOptions";

/**
 * Server and edge error reporting (E-13). Browser reporting is
 * `instrumentation-client.ts`; the settings for both are in
 * `foundation/observability`. Nothing starts without a DSN.
 */
export function register(): void {
  const options = sentryOptions("server", process.env);
  if (!options) return;
  Sentry.init({ ...options, beforeSend: (event) => scrubEvent(event) });
}

/** Errors thrown while rendering or handling a request on the server. */
export const onRequestError = Sentry.captureRequestError;
