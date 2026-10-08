import Link from "next/link";
import { HiOutlineBanknotes, HiOutlineUserGroup } from "react-icons/hi2";
import {
  AboutInfo,
  AboutInfoBullets,
  AboutInfoCallout,
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
 * The retiring client's `ReferralsInfo`, word for word. The figures match the
 * backend: `billing` charges the plan's 10%-off price when a code is given,
 * and `growth.domain.referral_reward_pence` credits £2.50 or £5. Change them
 * there and here together.
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
            description="£2.50 for each 1-month subscription, or £5.00 for each 3/6-month subscription."
          />
        </AboutInfoList>
      </AboutInfoSection>
      <AboutInfoSection title="Benefits for your friends" tone="green">
        <AboutInfoBullets
          items={[
            "10% discount on their subscription",
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
      <AboutInfoCallout label="Tip">
        Add your bank details to receive referral rewards once a referral has paid.
      </AboutInfoCallout>
    </AboutInfo>
  );
}
