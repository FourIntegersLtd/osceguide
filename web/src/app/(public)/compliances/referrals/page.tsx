import { SUPPORT_EMAIL } from "@/foundation/support";
import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";
import { LegalPage } from "@/domains/marketing/legal/LegalPage";

export const metadata: Metadata = publicPageMetadata({
  path: "/compliances/referrals",
  title: "Referral Program Terms & Conditions",
  description:
    "Review the terms and conditions for the OSCE Guide Referral Program, including eligibility, the 10% discount for friends, and the rewards referrers earn.",
});

export default function ReferralsPolicy() {
  return (
    <LegalPage doc="referrals" title="Referral Program Terms & Conditions">

      <div className="space-y-16">
        <section id="introduction">
          <h2 className="text-osce-title font-semibold mb-6">1. Introduction</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            These Terms and Conditions (&quot;Terms&quot;) govern your
            participation in the OSCE Guide Referral Program (&quot;Referral
            Program&quot;). By participating in the Referral Program, you agree
            to comply with these Terms. OSCE Guide is operated by Four Integers
            Ltd, a company registered in England and Wales.
          </p>
        </section>

        <section id="eligibility">
          <h2 className="text-osce-title font-semibold mb-6">2. Eligibility</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>You must be a registered OSCE Guide user aged 18 or over</li>
            <li>
              The Referral Program is only open to individual users for
              personal, non-commercial use
            </li>
            <li>
              You do not need to give OSCE Guide bank details to take part.
              Rewards are settled with you directly by the OSCE Guide team
            </li>
          </ul>
        </section>

        <section id="how-it-works">
          <h2 className="text-osce-title font-semibold mb-6">3. How It Works</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Each eligible user is issued a unique referral code, viewable in
              the &quot;Referral&quot; section of their account
            </li>
            <li>Share your referral code with friends and colleagues</li>
            <li>
              A friend who enters your code at checkout pays 10% less than the
              standard price of the plan they choose
            </li>
            <li>
              Your code can be used any number of times, by anyone but you
            </li>
            <li>
              Each completed purchase made with your code earns you £2.50 for a
              1-month plan, or £5 for a 3-month or 6-month plan. A reward is
              earned only once the payment has gone through
            </li>
          </ul>
        </section>

        <section id="reward-payments">
          <h2 className="text-osce-title font-semibold mb-6">4. Rewards</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Your referrals page shows your code, how many purchases were made
              with it, and the total you have earned
            </li>
            <li>
              The OSCE Guide team settles earned rewards with you directly. OSCE
              Guide does not store bank details for this programme
            </li>
            <li>
              A reward may be withheld for a purchase that is refunded, disputed
              or found to breach these Terms
            </li>
          </ul>
        </section>

        <section id="limits-conditions">
          <h2 className="text-osce-title font-semibold mb-6">
            5. Limits & Conditions
          </h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>There is no limit on the number of referrals you can make</li>
            <li>
              Self-referrals are strictly prohibited and will void eligibility
              for both parties
            </li>
            <li>
              Duplicate accounts, suspicious activity, or fraudulent use of
              referral codes will result in disqualification from the program
            </li>
          </ul>
        </section>

        <section id="tax-hmrc-compliance">
          <h2 className="text-osce-title font-semibold mb-6">
            6. Tax and HMRC Compliance
          </h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Any tax due on rewards you receive is your responsibility
            </li>
            <li>
              OSCE Guide is not responsible for your personal tax reporting or
              liabilities
            </li>
            <li>
              We reserve the right to request verification of identity for tax
              or compliance reasons
            </li>
          </ul>
        </section>

        <section id="termination-changes">
          <h2 className="text-osce-title font-semibold mb-6">
            7. Termination and Changes
          </h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Four Integers reserves the right to modify, suspend, or terminate
              the Referral Program or these Terms at any time, with or without
              notice
            </li>
            <li>
              Any fraudulent activity or abuse of the program may result in
              account suspension and forfeiture of rewards
            </li>
          </ul>
        </section>

        <section id="privacy-data">
          <h2 className="text-osce-title font-semibold mb-6">8. Privacy and Data</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Referral information (e.g., referrer and referee IDs) is processed
              securely in accordance with our Privacy Policy
            </li>
            <li>
              Bank details are not collected in the app for referrals. Rewards
              are settled with you directly
            </li>
          </ul>
        </section>

        <section id="governing-law">
          <h2 className="text-osce-title font-semibold mb-6">9. Governing Law</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            These Terms are governed by and construed in accordance with the
            laws of England and Wales. Any disputes arising from the Referral
            Program shall be subject to the exclusive jurisdiction of the courts
            of England and Wales.
          </p>
        </section>

        <section id="contact-information">
          <h2 className="text-osce-title font-semibold mb-6">10. Contact Us</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            If you have questions about the Referral Program, please contact us
            at:
          </p>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6 mt-4">
            <li>
              Email:{" "}
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="text-osce-accent hover:underline"
              >
                {SUPPORT_EMAIL}
              </a>
            </li>
          </ul>
        </section>
      </div>
    </LegalPage>
  );
}
