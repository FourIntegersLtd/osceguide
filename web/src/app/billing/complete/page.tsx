import type { Metadata } from "next";
import { Suspense } from "react";
import { PaymentReturn } from "@/capabilities/account";

export const metadata: Metadata = { title: "Payment" };

/**
 * Where Stripe sends somebody back after paying.
 *
 * This address is not a choice. `billing/service_checkout.py` builds
 * `success_url` as `{FRONTEND_URL}/billing/complete?session_id=…`, so the page
 * has to be here or a customer who has just paid lands on a 404 — which is the
 * worst 404 in the product.
 *
 * Outside every shell on purpose: they are arriving from another site and may
 * not have a resolved session yet.
 */
export default function Page() {
  return (
    <Suspense fallback={null}>
      <PaymentReturn />
    </Suspense>
  );
}
