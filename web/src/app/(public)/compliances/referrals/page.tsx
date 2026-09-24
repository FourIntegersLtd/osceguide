import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "OSCE Guide - Referral Program Terms & Conditions",
  description:
    "Review the terms and conditions for the OSCE Guide Referral Program, including eligibility, how a code is shared, and what the recorded balance means.",
  alternates: {
    canonical: "https://osceguide.com/compliances/referrals",
  },
};

export default function ReferralsPolicy() {
  return (
    <div className="py-12 max-w-4xl mx-auto justify-center">
      <h1 className="text-osce-heading font-bold mb-8">
        Referral Program Terms & Conditions
      </h1>
      <div className="space-y-6 mb-12">
        <p className="text-osce-body text-osce-ink-600">
          Effective Date: January 1, 2025
          <br />
          Last Updated: September 24, 2026
        </p>
      </div>

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
              A bank account is not required. This programme does not pay
              rewards by bank transfer
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
              When someone redeems your code, that redemption is counted on
              your referrals page
            </li>
            <li>
              A balance in pence may be recorded against those redemptions. It
              is a tally on your account, not a sum that will be paid out, and
              it does not change the price at checkout
            </li>
          </ul>
        </section>

        <section id="reward-payments">
          <h2 className="text-osce-title font-semibold mb-6">4. Recorded balance</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Your referrals page shows a code, how many people redeemed it,
              and a recorded balance
            </li>
            <li>
              That balance is not paid by bank transfer, and OSCE Guide does
              not store bank details for this programme
            </li>
            <li>
              Nothing on this page is a promise that the balance will be paid
              in the future
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
              A recorded referral balance is not a payment. If a payment
              programme is introduced later, tax on money you actually receive
              is your responsibility
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
              Bank details are not collected for referrals, because rewards are
              not transferred
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
                href="mailto:hello@fourintegers.com"
                className="text-osce-accent hover:underline"
              >
                hello@fourintegers.com
              </a>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
