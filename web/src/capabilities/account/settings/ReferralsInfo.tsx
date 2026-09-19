import Link from "next/link";
import { HiOutlineBanknotes, HiOutlineUserGroup } from "react-icons/hi2";
import {
  AboutInfo,
  AboutInfoBullets,
  AboutInfoHeader,
  AboutInfoIconMarker,
  AboutInfoItem,
  AboutInfoList,
  AboutInfoNote,
  AboutInfoSection,
} from "@/foundation/ui";

/**
 * What the referral programme is, in the modal beside the code.
 *
 * The reward figures the old copy quoted came from a consumer price list that
 * no longer decides anything — plans and their prices are the backend's — so
 * the terms are named and the numbers are left to the policy page rather than
 * printed here where they would drift.
 */
export default function ReferralsInfo() {
  return (
    <AboutInfo>
      <AboutInfoHeader
        title="Understanding our referral program"
        description="Share OSCE Guide with your friends and earn rewards while helping them with their exams."
      />
      <AboutInfoSection title="How it works" tone="sky">
        <AboutInfoList>
          <AboutInfoItem
            marker={
              <AboutInfoIconMarker>
                <HiOutlineUserGroup className="h-3.5 w-3.5" />
              </AboutInfoIconMarker>
            }
            title="Share your code"
            description="Generate your unique referral code and share it with friends."
          />
          <AboutInfoItem
            marker={
              <AboutInfoIconMarker className="border-osce-success-border bg-osce-success-bg text-osce-success-text">
                <HiOutlineBanknotes className="h-3.5 w-3.5" />
              </AboutInfoIconMarker>
            }
            title="Earn rewards"
            description="You earn on every subscription bought with your code. Your running total is on this page."
          />
        </AboutInfoList>
      </AboutInfoSection>
      <AboutInfoSection title="Benefits for your friends" tone="green">
        <AboutInfoBullets
          items={[
            "A discount on their subscription",
            "Full access to all OSCE Guide features including realistic patient interactions, instant feedback and detailed analytics across all domains",
            "Access to our OSCE Guide community and support forum",
          ]}
        />
      </AboutInfoSection>
      <AboutInfoNote>
        Please review our{" "}
        <Link
          href="/compliances/referrals"
          className="font-medium text-osce-accent hover:text-osce-accent-hover hover:underline"
        >
          Referral Program Policy
        </Link>{" "}
        for complete terms and conditions.
      </AboutInfoNote>
    </AboutInfo>
  );
}
