/*
 * One referral from the Referrals tab's history table: who joined, what it
 * earned and whether it has been paid. The retiring client's
 * `/settings/referrals/user/[id]`.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { ReferralDetail } from "@/capabilities/account";

export const metadata: Metadata = { title: "Referral details" };

export default async function Page({ params }: { params: Promise<{ referralId: string }> }) {
  const { referralId } = await params;
  return (
    <Capability id="account">
      <ReferralDetail referralId={referralId} />
    </Capability>
  );
}
