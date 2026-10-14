import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";
import { CheckoutCancelled } from "@/capabilities/account";
import { PricingSectionContent } from "@/domains/marketing/Pricing";

export const metadata: Metadata = publicPageMetadata({
  path: "/pricing",
  title: "Pricing",
  description:
    "Start with a free trial, then choose a 1, 3 or 6 month plan for SCA, PLAB 2, CASC or ortho interview practice with AI patients and structured feedback.",
});

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
      <PricingSectionContent asPageTitle />
    </main>
  );
}
