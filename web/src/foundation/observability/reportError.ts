import * as Sentry from "@sentry/nextjs";

/**
 * Report a failure that was caught and shown rather than thrown.
 *
 * An error boundary swallows what it catches, so nothing reaches Sentry's
 * global handlers; this is the one call a boundary makes. With no DSN set the
 * SDK was never started and this does nothing but log.
 */
export function reportError(error: unknown, context?: Record<string, string>): void {
  console.error(error);
  Sentry.captureException(error, context ? { tags: context } : undefined);
}
