import type { components } from "@/foundation/platform-client/schema";

/**
 * Every error code the platform API can return, as a union.
 *
 * Generated from the backend's OpenAPI document, where `ErrorResponse.code`
 * is an enum of the whole `AppError` hierarchy. A code that does not exist is
 * a compile error, and a code the backend removes breaks the build the next
 * time types are regenerated — which is the point.
 */
export type PlatformErrorCode = components["schemas"]["ErrorResponse"]["code"];

export type PlatformErrorBody = components["schemas"]["ErrorResponse"];

/**
 * A failed request, with the machine-readable parts kept.
 *
 * The B2B client's `toB2bFetchError` collapses a response into
 * `new Error(message)`, discarding the status and the body. Callers are then
 * left matching English: whether a trainee retries or is told the facilitator
 * ended the session turns on `message.includes("not live")`, and an
 * optimistic-concurrency conflict is `message.includes("another user")`.
 * Rewording a backend message silently changes what the app does.
 *
 * Switch on `code`. `message` is for showing a human, never for branching.
 */
export class PlatformError extends Error {
  readonly code: PlatformErrorCode;
  readonly status: number;
  readonly details: Record<string, unknown> | null;
  /** Correlates with the backend's structured logs. Worth putting in bug reports. */
  readonly requestId: string | null;

  constructor(status: number, body: PlatformErrorBody) {
    super(body.message);
    this.name = "PlatformError";
    this.status = status;
    this.code = body.code;
    this.details = body.details ?? null;
    this.requestId = body.request_id ?? null;
  }
}

/**
 * A request that never reached the API — offline, DNS, CORS, an abort.
 *
 * Distinct from `PlatformError` because there is no code to switch on and
 * retrying is usually right, whereas retrying a 409 is usually not.
 */
export class PlatformTransportError extends Error {
  readonly cause: unknown;

  constructor(message: string, cause: unknown) {
    super(message);
    this.name = "PlatformTransportError";
    this.cause = cause;
  }
}

export function isPlatformError(err: unknown): err is PlatformError {
  return err instanceof PlatformError;
}

/** `hasCode(err, "not_entitled", "trial_exhausted")` — narrows for the caller. */
export function hasCode(
  err: unknown,
  ...codes: readonly PlatformErrorCode[]
): err is PlatformError {
  return isPlatformError(err) && codes.includes(err.code);
}
