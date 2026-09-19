import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "OSCE Guide - Referral Program Terms & Conditions",
  description:
    "Review the terms and conditions for the OSCE Guide Referral Program, including eligibility, how it works, reward payments, and compliance.",
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
          Last Updated: May 14, 2025
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
              You must have a UK or international bank account to receive
              payments
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
              When a new user signs up using your code, they receive a 10%
              discount at checkout
            </li>
            <li>
              If the referred user completes a paid subscription, you earn:
              <ul className="list-disc list-inside ml-8 mt-2">
                <li>£2.50 for a 1-month subscription</li>
                <li>£5.00 for a 3-month or 6-month subscription</li>
              </ul>
            </li>
          </ul>
        </section>

        <section id="reward-payments">
          <h2 className="text-osce-title font-semibold mb-6">4. Reward Payments</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Referral rewards are paid via bank transfer to the bank account
              saved in your OSCE Guide profile
            </li>
            <li>
              Payments are processed within 48 hours of the referred user&apos;s
              subscription being confirmed and payment successfully received
            </li>
            <li>
              Users are responsible for ensuring their bank details are accurate
              and up to date
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
              All referral earnings constitute personal income and may be
              taxable
            </li>
            <li>
              It is your responsibility to report referral income to HMRC as
              required by UK tax law
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
              Bank details are stored securely and used only for the purpose of
              transferring referral rewards
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
