import type { Metadata } from "next";
import { ReferralPayouts } from "@/domains/platform";

export const metadata: Metadata = { title: "Referral payouts" };

export default function Page() {
  return <ReferralPayouts />;
}
