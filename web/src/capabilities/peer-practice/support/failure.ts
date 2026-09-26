import { PlatformError } from "@/foundation/platform-client";

/**
 * The server's own sentence when it sent one, else the retiring client's
 * fallback for that action — which is what its `getErrorMessage(err, fallback)`
 * did. A dropped connection gets the fallback rather than a transport message.
 */
export function failureText(cause: unknown, fallback: string): string {
  return cause instanceof PlatformError && cause.message ? cause.message : fallback;
}
