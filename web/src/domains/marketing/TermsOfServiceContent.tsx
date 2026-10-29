import { SUPPORT_EMAIL } from "@/foundation/support";
import { LegalPage } from "@/domains/marketing/legal/LegalPage";
/** Terms of Service copy for the compliance page. */
export default function TermsOfServiceContent() {
  return (
    <LegalPage doc="terms" title="Terms of Service">

      <div className="space-y-6 mb-12">
        <p className="text-osce-ink-700 leading-relaxed">
          Welcome to OSCE Guide! These Terms of Service (&quot;Terms&quot;)
          govern your use of OSCE Guide. By accessing or using the platform, you
          agree to be bound by these Terms.
        </p>
      </div>

      <div className="space-y-16">
        <section id="introduction">
          <h2 className="text-osce-title font-semibold mb-6">1. Introduction</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            OSCE Guide is an educational platform designed to help medical
            professionals prepare for Objective Structured Clinical Examinations
            (OSCEs). The platform provides simulated consultations, AI-generated
            feedback, and performance metrics.
          </p>
        </section>

        <section id="eligibility">
          <h2 className="text-osce-title font-semibold mb-6">2. Eligibility</h2>
          <p className="text-osce-ink-700 leading-relaxed">You must:</p>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 mt-4 ml-6">
            <li>Be at least 18 years old.</li>
            <li>Be a qualified or student medical professional.</li>
          </ol>
          <p className="text-osce-ink-700 leading-relaxed mt-4">
            By using the platform, you confirm that you meet these requirements.
          </p>
        </section>

        <section id="services-provided">
          <h2 className="text-osce-title font-semibold mb-6">3. Services Provided</h2>
          <p className="text-osce-ink-700 leading-relaxed">OSCE Guide offers:</p>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 mt-4 ml-6">
            <li>Real-time OSCE simulation scenarios.</li>
            <li>AI-generated performance feedback.</li>
            {/* <li>Progress tracking and performance metrics.</li> */}
          </ol>
          <p className="text-osce-ink-700 leading-relaxed mt-4">
            Disclaimer: OSCE Guide is an educational tool and does not replace
            formal medical training or regulatory requirements.
          </p>
        </section>

        <section id="user-obligations">
          <h2 className="text-osce-title font-semibold mb-6">4. User Obligations</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            By using OSCE Guide, you agree to:
          </p>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 mt-4 ml-6">
            <li>Use the platform only for lawful, educational purposes.</li>
            <li>Not share your login credentials.</li>
            <li>
              Not use the platform to upload offensive, inaccurate, or unlawful
              content.
            </li>
          </ol>
          <p className="text-osce-ink-700 leading-relaxed mt-4">
            You are responsible for ensuring the platform aligns with your
            educational or training needs.
          </p>
        </section>

        <section id="intellectual-property">
          <h2 className="text-osce-title font-semibold mb-6">
            5. Intellectual Property
          </h2>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              All content, software, and features of OSCE Guide are the
              exclusive property of the platform.
            </li>
            <li>
              You are granted a limited, non-exclusive, non-transferable licence
              to use the platform for personal, educational purposes.
            </li>
            <li>
              You may not copy, distribute, modify, or create derivative works
              from the platform&apos;s content.
            </li>
          </ol>
        </section>

        <section id="ai-generated-feedback">
          <h2 className="text-osce-title font-semibold mb-6">
            6. AI-Generated Feedback
          </h2>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              OSCE Guide uses third-party AI services (e.g., Eleven Labs,
              OpenAI, Anthropic) for real-time speech processing and feedback
              generation.
            </li>
            <li>
              AI-generated feedback is for educational purposes only and may not
              always reflect the judgment of a qualified medical professional.
            </li>
            <li>
              Users are encouraged to consult with qualified trainers for
              detailed guidance.
            </li>
          </ol>
        </section>

        <section id="payments-and-refund-policy">
          <h2 className="text-osce-title font-semibold mb-6">
            7. Payments and Subscription Policy
          </h2>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              <span className="font-medium">Subscription Model:</span>
              <ul className="list-disc list-inside space-y-2 ml-6 mt-2">
                <li>We offer 1, 3, and 6-month fixed-duration subscriptions</li>
                <li>
                  Each subscription requires a new purchase - we don&apos;t
                  auto-renew
                </li>
                <li>
                  Access to the station catalogue is limited as described under
                  &quot;Station catalogue access by subscription&quot; below
                </li>
              </ul>
            </li>
            <li>
              <span className="font-medium">Service Delivery:</span>
              <ul className="list-disc list-inside space-y-2 ml-6 mt-2">
                <li>
                  Access to your allocated stations is provided instantly after
                  payment
                </li>
                <li>
                  Each station you access or complete counts as delivered
                  service
                </li>
                <li>
                  Your progress and completion status are permanently recorded
                </li>
              </ul>
            </li>
            <li>
              <span className="font-medium">Payment Terms:</span>
              <p className="ml-6 mt-2">
                By accepting these terms and making a payment, you acknowledge
                that:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-6 mt-2">
                <li>Each subscription is a separate purchase agreement</li>
                <li>
                  Payments become non-refundable once you access any station
                </li>
                <li>
                  Payment disputes after accessing stations breach these terms
                </li>
              </ul>
            </li>
          </ol>
          <h3
            id="station-catalogue-access"
            className="text-osce-subheading font-semibold mb-4 mt-10 ml-6 scroll-mt-24"
          >
            Station catalogue access by subscription
          </h3>
          <p className="text-osce-ink-700 leading-relaxed ml-6 mb-4">
            The number of stations you may access from our catalogue depends on
            your subscription plan, exam product (e.g. SCA, PLAB, CASC, Ortho),
            and your account status in the Service. Eligible stations may also
            be filtered by release date, approval status, and your own progress
            (for example, stations you have already attempted). The figures
            below are the current caps we apply in the platform for catalogue
            access; we may adjust them with notice in line with &quot;Changes to
            the Terms&quot;.
          </p>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-10 mb-6">
            <li>
              <span className="font-medium">
                One-month subscription (active):
              </span>{" "}
              access is limited to a maximum of{" "}
              <span className="font-medium">53</span> eligible stations per exam
              product (for SCA and PLAB; other exam products follow the same
              numeric cap where the Service applies a one-month limit).
            </li>
            <li>
              <span className="font-medium">
                One-month plan with a lapsed or expired subscription flag:
              </span>{" "}
              until your account status is updated (for example after you log in
              following a renewal), the Service may allow access to a larger
              capped catalogue of up to <span className="font-medium">78</span>{" "}
              eligible stations for that exam product. Once your subscription is
              active and your account reflects current access, the{" "}
              <span className="font-medium">53</span>-station limit for an
              active one-month subscription applies again as described above.
            </li>
            <li>
              <span className="font-medium">
                Three-month and six-month subscriptions:
              </span>{" "}
              there is no additional fixed cap on the number of eligible
              stations beyond the total stations available in the catalogue for
              your exam product, subject to the same eligibility and filtering
              rules.
            </li>
            <li>
              <span className="font-medium">Mocks and selections:</span> the
              number of stations included in a single mock or session is also
              subject to the options available in the Service and any limits you
              select at the time of creating a mock.
            </li>
          </ul>
          <p className="text-osce-ink-700 mt-4 ml-6 font-semibold italic">
            Questions? Contact {SUPPORT_EMAIL} before purchasing.
          </p>
        </section>

        <section id="limitations-of-liability">
          <h2 className="text-osce-title font-semibold mb-6">
            8. Limitations of Liability
          </h2>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              OSCE Guide is provided &quot;as is&quot; and &quot;as
              available.&quot;
            </li>
            <li>
              We make no guarantees about the accuracy, reliability, or
              completeness of AI-generated feedback or other content.
            </li>
            <li>
              To the fullest extent permitted by law, we are not liable for:
            </li>
          </ol>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-10 mt-4">
            <li>Any indirect, incidental, or consequential damages.</li>
            <li>Loss of data, profits, or educational opportunities.</li>
          </ul>
        </section>

        <section id="force-majeure">
          <h2 className="text-osce-title font-semibold mb-6">9. Force Majeure</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We are not responsible for delays or failures in performance caused
            by events beyond our reasonable control, including but not limited
            to:
          </p>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6 mt-4">
            <li>Natural disasters</li>
            <li>Government actions</li>
            <li>Third-party service outages</li>
            <li>Technical failures</li>
          </ul>
        </section>

        <section id="termination">
          <h2 className="text-osce-title font-semibold mb-6">10. Termination</h2>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              We reserve the right to suspend or terminate your account if you
              violate these Terms or engage in unlawful activity.
            </li>
            <li>
              You may terminate your account at any time by contacting support.
            </li>
          </ol>
        </section>

        <section id="dispute-resolution">
          <h2 className="text-osce-title font-semibold mb-6">
            11. Dispute Resolution
          </h2>
          <ol className="list-decimal list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Any disputes will first be resolved through good-faith
              discussions.
            </li>
            <li>
              If unresolved, disputes will be referred to mediation under UK
              law.
            </li>
            <li>
              If mediation fails, disputes will be subject to arbitration or
              court proceedings in the jurisdiction specified below.
            </li>
          </ol>
        </section>

        <section id="governing-law">
          <h2 className="text-osce-title font-semibold mb-6">12. Governing Law</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            These Terms are governed by the laws of England and Wales. Any
            disputes will be subject to the exclusive jurisdiction of the courts
            of England and Wales.
          </p>
        </section>

        <section id="changes-to-the-terms">
          <h2 className="text-osce-title font-semibold mb-6">
            13. Changes to the Terms
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We may update these Terms from time to time. Material changes will
            be communicated via email or platform notification. Continued use of
            the platform constitutes acceptance of the updated Terms.
          </p>
        </section>

        <section id="ai-model-training">
          <h2 className="text-osce-title font-semibold mb-6">14. AI Model Training</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Users can opt in to contribute their consultation data for AI model
            improvement. This includes anonymized transcripts, feedback, and
            performance data. While consent can be withdrawn anytime through
            account settings, previously derived insights may persist in our
            models. We comply with GDPR and other applicable data protection
            laws, using personally identifiable information only with explicit
            consent.
          </p>
        </section>

        <section id="contact-information">
          <h2 className="text-osce-title font-semibold mb-6">
            15. Contact Information
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            For any questions or concerns about these Terms, contact us at:
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
