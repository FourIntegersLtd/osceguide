import { isPlatformError } from "@/foundation/platform-client/errors";

/** Stripe's webhook can land a beat after the redirect; ask briefly. */
export const CONFIRM_ATTEMPTS = 6;
export const CONFIRM_INTERVAL_MS = 2000;

/**
 * What the page Stripe returns to can honestly say.
 *
 * - `paid`: this very checkout session has a receipt, so the webhook has granted the access.
 * - `signed_out`: the receipts question was refused as unauthenticated, so nothing can be
 *   confirmed until the buyer signs in (a new browser, or the session ended while they paid).
 * - `pending`: no receipt yet, or the question kept failing; the payment may well have gone through.
 */
export type PaymentOutcome = "paid" | "signed_out" | "pending";

/**
 * Ask for this checkout session's receipts until one appears.
 *
 * It asks about the session in the address, not about entitlements: a renewal, a trial row or an
 * earlier purchase already makes someone "entitled", which read as a payment confirmed seconds
 * after paying. A 401 ends the wait at once; any other failure is retried like an empty answer.
 */
export async function confirmPayment(
  receiptsForSession: () => Promise<readonly unknown[]>,
  wait: (ms: number) => Promise<void>,
  isCancelled: () => boolean,
): Promise<PaymentOutcome> {
  for (let attempt = 1; attempt <= CONFIRM_ATTEMPTS; attempt += 1) {
    try {
      if ((await receiptsForSession()).length > 0) return "paid";
    } catch (cause) {
      if (isPlatformError(cause) && cause.status === 401) return "signed_out";
    }
    if (isCancelled()) return "pending";
    if (attempt < CONFIRM_ATTEMPTS) await wait(CONFIRM_INTERVAL_MS);
  }
  return "pending";
}
