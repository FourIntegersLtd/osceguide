import { PlatformError } from "@/foundation/platform-client";

/**
 * What a small action's toast says when it failed: the server's own sentence when it refused
 * (a missing station, no access), else the retry line for a dropped connection.
 */
export function actionFailureText(cause: unknown): string {
  return cause instanceof PlatformError && cause.message ? cause.message : "Please try again in a moment.";
}
