import type { Metadata } from "next";
import { CheckoutCancelled } from "@/capabilities/account";

export const metadata: Metadata = { title: "Pricing" };

/**
 * Where Stripe sends somebody who changed their mind.
 *
 * The backend's `cancel_url` is `{FRONTEND_URL}/pricing`, so this address is
 * fixed for the same reason `/billing/complete` is. Public, because cancelling
 * is not a signed-in act and the landing's own pricing section is what a
 * visitor typing this URL expects.
 */
export default function Page() {
  return <CheckoutCancelled />;
}
