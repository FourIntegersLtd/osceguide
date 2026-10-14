import { COMPLIANCE_DATES, SUPPORT_EMAIL } from "@/foundation/support";
import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";

export const metadata: Metadata = publicPageMetadata({
  path: "/compliances/legal-disclaimer",
  title: "Legal Disclaimer",
  description:
    "Read the legal disclaimer for OSCE Guide, covering ownership of content, no guarantee of success, educational use, and limitations of liability.",
});

export default function LegalDisclaimer() {
  return (
    <div className="py-12 px-6 sm:px-8 max-w-4xl mx-auto justify-center">
      <h1 className="text-osce-heading font-bold mb-8">Legal Disclaimer</h1>

      <div className="space-y-6 mb-12">
        <p className="text-osce-body text-osce-ink-600">
          Effective Date: {COMPLIANCE_DATES.disclaimer.effective}
          <br />
          Last Updated: {COMPLIANCE_DATES.disclaimer.updated}
        </p>
        <p className="text-osce-ink-700 leading-relaxed">
          <strong>OSCE Guide </strong>is a platform designed to assist doctors
          in simulating clinical consultations using a voice AI model. Users can
          receive AI-generated feedback, listen to AI-generated podcasts, and
          engage in debriefing sessions with an AI tutor. By using this
          platform, you acknowledge that you have read and understood the terms
          and conditions, including the limitations of liability and the use of
          AI-generated feedback. If you have any questions, please contact us at
          &quot;{SUPPORT_EMAIL}&quot;.
        </p>
      </div>

      <div className="space-y-16">
        <section>
          <h2 className="text-osce-title font-semibold mb-6"> Definitions</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            For the purposes of this disclaimer, the following terms shall have
            the meanings ascribed to them:
            <ul className="list-disc pl-6">
              <li>
                <strong>Platform:</strong> Refers to the OSCE Guide application
                and all associated services.
              </li>
              <li>
                <strong>User:</strong> Any individual who accesses or uses the
                Platform.
              </li>
              <li>
                <strong>Content:</strong> All materials, information, and
                resources available on the Platform.
              </li>
            </ul>
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            1. Ownership of Content
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            All cases presented on OSCE Guide are created by Four Integers
            Limited and are protected under intellectual property laws.
            Unauthorized reproduction or distribution of these cases is strictly
            prohibited without prior written consent.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            2. No Guarantee of Success
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            While OSCE Guide is a valuable resource, Four Integers Limited does
            not guarantee that your use of the platform will result in passing
            your exam. We recommend using OSCE Guide as one of several tools in
            your study plan.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">3. Nature of Cases</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            The cases provided are fictional and designed to reflect common
            scenarios encountered by general practitioners. Any similarity to
            actual cases in the SCA exam is coincidental. The RCGP has a diverse
            bank of cases, and the selection process is independent of our
            platform.
          </p>
        </section>
        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            8. Feedback and Debrief
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            The feedback provided by OSCE Guide is designed to offer a general
            overview of your progress. However, please remember that every
            consultation analysis is intended solely for formative training
            purposes. It should not be interpreted as an accurate reflection of
            your expected performance in the actual exam. Furthermore, due to
            the inherent limitations of AI-generated feedback, it may not fully
            encompass the complexities of your learning journey and performance.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            4. Educational Use Only
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            The medical information available on OSCE Guide is intended solely
            for educational purposes and should not be used for patient care. We
            strive to keep this information current, but we do not guarantee its
            accuracy or completeness.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">5. External Links</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Our website may contain links to external sites. Four Integers
            Limited does not control these sites and is not responsible for
            their content or accuracy. Inclusion of a link does not imply
            endorsement of the linked site.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">6. Cookie Policy</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            This website uses cookies to enhance user experience. Please refer
            to our cookie policy for more information.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            7. Subscription Cancellation
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Four Integers Limited reserves the right to terminate your
            subscription if it is discovered that you are reproducing our
            content without permission. It is your responsibility to cancel your
            subscription upon completion of your use of OSCE Guide, as we do not
            automatically cancel subscriptions.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            8. Limitation of Liability
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Four Integers Limited shall not be liable for any direct, indirect,
            incidental, special, consequential, or punitive damages arising from
            your use of or inability to use the OSCE Guide platform, even if we
            have been advised of the possibility of such damages, to the maximum
            extent permitted by law.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">9. Indemnification</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            You agree to indemnify, defend, and hold harmless Four Integers
            Limited and its affiliates, officers, directors, employees, and
            agents from any claims, liabilities, damages, losses, or expenses,
            including reasonable attorneys&apos; Fees, arising out of or related to
            your use of the OSCE Guide platform or violation of these terms.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">10. Governing Law</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            These terms shall be governed by and construed in accordance with
            the laws of the United Kingdom, without regard to its conflict of
            law principles. Any disputes arising under or in connection with
            these terms shall be subject to the exclusive jurisdiction of the
            courts located in the United Kingdom.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">11. Changes to Terms</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Four Integers Limited reserves the right to modify these terms at
            any time. We will notify you of any changes by posting the new terms
            on this page. Your continued use of the platform after any changes
            constitutes your acceptance of the new terms.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            12. User Responsibilities
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Users are responsible for ensuring that their use of the OSCE Guide
            platform complies with all applicable laws and regulations. Users
            must not use the platform for any unlawful purpose or in a manner
            that could damage, disable, or impair the platform.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            13. Disclaimer of Warranties
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            The OSCE Guide platform is provided on an &quot;as is&quot; And &quot;as available&quot;
            basis. Four Integers Limited makes no representations or warranties
            of any kind, express or implied, regarding the operation of the
            platform or the information, content, materials, or products
            included on the platform. To the fullest extent permissible by
            applicable law, Four Integers Limited disclaims all warranties,
            express or implied, including, but not limited to, implied
            warranties of merchantability and fitness for a particular purpose.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">14. Force Majeure</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Four Integers Limited shall not be liable for any failure to perform
            its obligations under these terms where such failure results from
            any cause beyond Four Integers Limited&apos;s reasonable control,
            including, but not limited to, mechanical, electronic, or
            communications failure or degradation.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">15. Severability</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            If any provision of these terms is found to be unenforceable or
            invalid, that provision will be limited or eliminated to the minimum
            extent necessary so that the remaining provisions of these terms
            will remain in full force and effect.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">16. User Consent</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            By accessing or using the OSCE Guide platform, you acknowledge that
            you have read, understood, and agree to be bound by these terms and
            conditions. If you do not agree to these terms, you must not use the
            platform.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">17. Privacy Policy</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Your privacy is important to us. Please refer to our{" "}
            <a
              href="/compliances/privacy-policy"
              className="text-osce-accent underline"
            >
              Privacy Policy
            </a>{" "}
            for information on how we collect, use, and protect your personal
            data.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            18. Dispute Resolution
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Any disputes arising out of or related to these terms shall be
            resolved through binding arbitration in accordance with the rules of
            the Chartered Institute of Arbitrators (CIArb). The arbitration
            shall take place in London, United Kingdom, and the decision of the
            arbitrator shall be final and binding.
          </p>
        </section>
      </div>
    </div>
  );
}
