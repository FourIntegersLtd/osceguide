import type { Metadata } from "next";
import { CheckoutCancelled } from "@/capabilities/account";
import { LandingPricingSection } from "@/domains/marketing/sections/LandingPricingSection";

export const metadata: Metadata = { title: "Pricing" };

/**
 * The pricing page, and where Stripe sends somebody who changed their mind.
 *
 * These are two visitors and the page used to answer both with the cancel
 * card, so anybody who typed `/pricing` — or followed the redirect from an
 * old `/payments/*` bookmark — was told "Checkout cancelled. No payment was
 * taken" about a checkout they never started. The backend's `cancel_url` is
 * `{FRONTEND_URL}/pricing?cancelled=1` (billing/service_checkout.py), so the
 * cancel card is the answer to that query and to nothing else.
 */
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ cancelled?: string }>;
}) {
  const { cancelled } = await searchParams;
  if (cancelled !== undefined) return <CheckoutCancelled />;
  return (
    <main>
      <LandingPricingSection />
    </main>
  );
}
