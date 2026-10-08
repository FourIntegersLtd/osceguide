import { hasCode, isPlatformError } from "@/foundation/platform-client/errors";

/**
 * What to tell somebody whose checkout was refused.
 *
 * A refusal the buyer can fix is said plainly; anything else is ours, and they need to hear that no
 * money moved (the refusal comes before Stripe is asked for a payment).
 */
export function checkoutErrorMessage(cause: unknown, supportEmail: string): string {
  if (hasCode(cause, "referral_not_found")) {
    return "That referral code is not valid. Check it, or clear it to pay the full price.";
  }
  if (hasCode(cause, "referral_discount_unavailable")) {
    return "That plan has no referral discount. Choose another plan, or clear the code.";
  }
  // Not in the generated code union until `schema.d.ts` is regenerated from the API. The server's
  // message says what to do, so it is shown as it is.
  if (isPlatformError(cause) && (cause.code as string) === "already_purchased") {
    return cause.message;
  }
  if (hasCode(cause, "plan_not_available")) {
    return "That plan is not available for your exam. Choose another plan.";
  }
  const detail = isPlatformError(cause) ? cause.message : "We could not start your payment.";
  return `${detail} No money has left your account. Please try again or email ${supportEmail}.`;
}
