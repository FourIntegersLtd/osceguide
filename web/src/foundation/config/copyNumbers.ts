/**
 * Numbers in UI copy that more than one feature shows. A single feature's numbers live in its own
 * capability (`peer-practice/limits.ts`, `media/limits.ts`).
 *
 * `scripts/check-copy-numbers.mjs` fails on "30 days", "10 minutes", "500 characters" typed into a
 * .tsx file. The password length lives with its rule in foundation/session/temporaryPassword.ts;
 * plan figures (stations, prices) come from the API's PlanRead, never from here.
 */

/** A closed account can be reopened by signing in within this many days; then erasure runs (api `service_erasure`). */
export const ACCOUNT_REOPEN_DAYS = 30;
/** After a password change, other devices are signed out within this many minutes (access token life). */
export const OTHER_DEVICES_SIGN_OUT_MINUTES = 15;
/** The support reply time the site promises. */
export const SUPPORT_REPLY_HOURS = 12;
