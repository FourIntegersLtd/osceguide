import type { Metadata } from "next";
import { SITE_URL } from "@/foundation/config/siteUrl";

export const metadata: Metadata = {
  title: "OSCE Guide - Privacy Policy",
  description:
    "Understand how OSCE Guide collects, uses, and protects your personal data. Learn about your data rights and our commitment to privacy.",
  alternates: {
    canonical: `${SITE_URL}/compliances/privacy-policy`,
  },
};

export default function PrivacyPolicy() {
  return (
    <div className="py-12  max-w-4xl mx-auto justify-center">
      <h1 className="text-osce-heading font-bold mb-8">Privacy Policy</h1>

      <div className="space-y-6 mb-12">
        <p className="text-osce-body text-osce-ink-600">
          Effective Date: January 1, 2025
          <br />
          Last Updated: May 4, 2025
        </p>
        <p className="text-osce-ink-700 leading-relaxed">
          OSCE Guide (&quot;we,&quot; &quot;us,&quot; &quot;our&quot;) provides
          an AI-powered OSCE simulation platform for medical professionals. This
          privacy policy outlines our commitment to protecting your personal
          data and privacy rights while using our service.
        </p>
      </div>

      <div className="mb-12">
        <h2 className="text-osce-title font-semibold mb-6">Table of Contents</h2>
        <ol className="list-decimal list-inside space-y-2 text-osce-ink-700 ml-4">
          {[
            "Introduction",
            "Definitions",
            "Data Controller Information",
            "Data We Collect",
            "How We Use Your Data",
            "AI Processing and Third-Party Services",
            "International Data Transfers",
            "Your Rights",
            "Data Security",
            "Data Retention",
            "Changes to This Policy",
            "Contact Information",
          ].map((item, index) => (
            <li key={index} className="hover:text-osce-accent cursor-pointer">
              <a href={`#${item.toLowerCase().replace(/\s+/g, "-")}`}>{item}</a>
            </li>
          ))}
        </ol>
      </div>

      <div className="space-y-16">
        <section id="introduction">
          <h2 className="text-osce-title font-semibold mb-6">1. Introduction</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            OSCE Guide (&quot;we,&quot; &quot;us,&quot; &quot;our&quot;)
            provides an AI-powered OSCE simulation platform for medical
            professionals. This privacy policy outlines our commitment to
            protecting your personal data and privacy rights while using our
            service.
          </p>
        </section>

        <section id="definitions">
          <h2 className="text-osce-title font-semibold mb-6">2. Definitions</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              <strong>OSCE:</strong> Objective Structured Clinical Examination
            </li>
            <li>
              <strong>Application:</strong> Our medical OSCE simulation platform
            </li>
            <li>
              <strong>User:</strong> Medical professionals using our application
            </li>
            <li>
              <strong>AI Services:</strong> Our third-party artificial
              intelligence service providers
            </li>
            <li>
              <strong>Transcript:</strong> Text record of simulated
              consultations
            </li>
            <li>
              <strong>Feedback:</strong> AI-generated assessment of performance
            </li>
          </ul>
        </section>

        <section id="data-controller-information">
          <h2 className="text-osce-title font-semibold mb-6">
            3. Data Controller Information
          </h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              <strong>Company:</strong> Four Integers Ltd
            </li>
            <li>
              <strong>Email:</strong> hello@fourintegers.com
            </li>
            <li>
              <strong>Data Protection Officer:</strong>{" "}
              aishat.abubakar@fourintegers.com
            </li>
          </ul>
        </section>

        <section id="data-we-collect">
          <h2 className="text-osce-title font-semibold mb-6">4. Data We Collect</h2>
          <div className="space-y-6">
            <div>
              <h3 className="font-semibold mb-4">4.1 Account Information</h3>
              <ul className="list-disc list-inside text-osce-ink-700 ml-6">
                <li>Email address</li>
                <li>Username</li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">4.2 Consultation Data</h3>
              <ul className="list-disc list-inside text-osce-ink-700 ml-6">
                <li>Consultation transcripts</li>
                <li>AI-generated feedback</li>
                <li>Performance metrics</li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">4.3 Technical Data</h3>
              <ul className="list-disc list-inside text-osce-ink-700 ml-6">
                <li>IP address</li>
                <li>Browser type</li>
                <li>Device information</li>
                <li>Access logs</li>
              </ul>
            </div>
          </div>
        </section>

        <section id="how-we-use-your-data">
          <h2 className="text-osce-title font-semibold mb-6">
            5. How We Use Your Data
          </h2>
          <div className="space-y-6">
            <div>
              <h3 className="font-semibold mb-4">5.1 Primary Purposes</h3>
              <ul className="list-disc list-inside text-osce-ink-700 ml-6">
                <li>Account creation and management</li>
                <li>Providing simulation services</li>
                <li>Generating performance feedback</li>
                <li>Service improvement and optimization</li>
                <li>Analyzing user behavior and engagement through Google Analytics</li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">
                5.2 Legal Bases for Processing
              </h3>
              <ul className="list-disc list-inside text-osce-ink-700 ml-6">
                <li>
                  <strong>Contract Performance:</strong> Account management and
                  service provision
                </li>
                <li>
                  <strong>Consent:</strong> AI processing and feedback
                  generation
                </li>
                <li>
                  <strong>Legitimate Interests:</strong> Service improvement and
                  security
                </li>
              </ul>
            </div>
          </div>
        </section>

        <section id="ai-processing-and-third-party-services">
          <h2 className="text-osce-title font-semibold mb-6">
            6. AI Processing and Third-Party Services
          </h2>
          <div className="space-y-6">
            <p className="text-osce-ink-700 leading-relaxed">
              We carefully select our third-party service providers based on
              their commitment to data security and compliance with relevant
              regulations. We ensure that any data shared with these providers
              is done so in accordance with our privacy policy and applicable
              laws.
            </p>

            <p className="text-osce-ink-700 leading-relaxed">
              As part of our commitment to continuous improvement, we offer
              users the option to contribute their data to enhance our AI
              models. This includes consultation transcripts, AI-generated
              feedback, and performance metrics. This data helps us develop more
              personalized recommendations and improve the overall quality of
              our service.
            </p>

            <p className="text-osce-ink-700 leading-relaxed">
              In compliance with GDPR requirements, we implement strict data
              protection measures for AI training. Users must provide explicit
              consent before their data is used for training purposes, and this
              consent can be withdrawn at any time through the account settings.
              All training data is pseudonymized to protect user privacy and
              stored securely within the EU/EEA. We conduct regular audits to
              ensure ongoing compliance with data protection laws and maintain
              transparency in our data processing practices.
            </p>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-osce-border">
                <thead className="bg-osce-canvas">
                  <tr>
                    <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                      Provider
                    </th>
                    <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                      Purpose
                    </th>
                    <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                      Data Processed
                    </th>
                    <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                      Location
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-osce-border">
                  <tr>
                    <td className="px-6 py-4">
                      Real-Time Communication Service
                    </td>
                    <td className="px-6 py-4">
                      Facilitating real-time audio and video interactions
                    </td>
                    <td className="px-6 py-4">Audio and video data</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Eleven Labs</td>
                    <td className="px-6 py-4">Speech processing</td>
                    <td className="px-6 py-4">Audio Data</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">OpenAI</td>
                    <td className="px-6 py-4">Feedback generation</td>
                    <td className="px-6 py-4">Consultation transcripts</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Anthropic</td>
                    <td className="px-6 py-4">Feedback generation</td>
                    <td className="px-6 py-4">Consultation transcripts</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Google Cloud Storage</td>
                    <td className="px-6 py-4">Data storage</td>
                    <td className="px-6 py-4">Account data, transcripts</td>
                    <td className="px-6 py-4">EU</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">AWS EC2</td>
                    <td className="px-6 py-4">Cloud computing</td>
                    <td className="px-6 py-4">Application data</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Stripe</td>
                    <td className="px-6 py-4">Payment processing</td>
                    <td className="px-6 py-4">Payment information</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Deepgram</td>
                    <td className="px-6 py-4">Speech processing</td>
                    <td className="px-6 py-4">Audio data</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Cartesia</td>
                    <td className="px-6 py-4">Speech processing</td>
                    <td className="px-6 py-4">Audio data</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4">Google Analytics</td>
                    <td className="px-6 py-4">Website analytics</td>
                    <td className="px-6 py-4">User interaction data</td>
                    <td className="px-6 py-4">USA</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section id="international-data-transfers">
          <h2 className="text-osce-title font-semibold mb-6">
            7. International Data Transfers
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We transfer data to the United States for processing by our AI
            service providers. These transfers are protected by:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-osce-ink-700 ml-6">
            <li>
              <strong>Standard Contractual Clauses (SCCs)</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>EU-approved data transfer mechanisms</li>
                <li>Regular transfer impact assessments</li>
                <li>Additional security measures</li>
              </ul>
            </li>
            <li>
              <strong>Security Measures</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>End-to-end encryption</li>
                <li>Data minimization</li>
                <li>Immediate processing and results return</li>
              </ul>
            </li>
          </ol>
        </section>

        <section id="your-rights">
          <h2 className="text-osce-title font-semibold mb-6">8. Your Rights</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            You have the following rights:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-osce-ink-700 ml-6">
            <li>
              <strong>Access Rights</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>Request copies of your data</li>
                <li>View stored transcripts</li>
                <li>Access feedback history</li>
              </ul>
            </li>
            <li>
              <strong>Control Rights</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>Update account information</li>
                <li>Delete your data</li>
                <li>Export your information</li>
              </ul>
            </li>
            <li>
              <strong>Additional Rights</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>Withdraw processing consent</li>
                <li>Object to processing</li>
                <li>File regulatory complaints</li>
              </ul>
            </li>
          </ol>
          <p className="text-osce-ink-700 leading-relaxed">
            To exercise these rights, contact us at{" "}
            <a
              href="mailto:privacy@fourintegers.com"
              className="text-osce-accent hover:underline"
            >
              privacy@fourintegers.com
            </a>
          </p>
        </section>

        <section id="data-security">
          <h2 className="text-osce-title font-semibold mb-6">9. Data Security</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We implement appropriate security measures:
          </p>
          <ol className="list-decimal list-inside space-y-2 text-osce-ink-700 ml-6">
            <li>
              <strong>Technical Measures</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>End-to-end encryption</li>
                <li>Secure data transmission</li>
                <li>Access controls</li>
                <li>Regular security testing</li>
              </ul>
            </li>
            <li>
              <strong>Organizational Measures</strong>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li>Staff training</li>
                <li>Access restrictions</li>
                <li>Security policies</li>
                <li>Incident response procedures</li>
              </ul>
            </li>
          </ol>
        </section>

        <section id="data-retention">
          <h2 className="text-osce-title font-semibold mb-6">10. Data Retention</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We retain your data as follows:
          </p>
          <div className="overflow-x-auto my-4">
            <table className="min-w-full divide-y divide-osce-border">
              <thead className="bg-osce-canvas">
                <tr>
                  <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                    Data Type
                  </th>
                  <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                    Retention Period
                  </th>
                  <th className="px-6 py-3 text-left text-osce-caption font-medium text-osce-ink-500 uppercase">
                    Reason
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-osce-border">
                <tr>
                  <td className="px-6 py-4">Account Data</td>
                  <td className="px-6 py-4">Duration of account + 30 days</td>
                  <td className="px-6 py-4">Service provision</td>
                </tr>
                <tr>
                  <td className="px-6 py-4">Transcripts</td>
                  <td className="px-6 py-4">Duration of account + 30 days</td>
                  <td className="px-6 py-4">
                    Performance review and educational analysis
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4">Feedback</td>
                  <td className="px-6 py-4">Duration of account + 30 days</td>
                  <td className="px-6 py-4">
                    Progress tracking and personalized improvements
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4">Payment Records</td>
                  <td className="px-6 py-4">6 years from transaction date</td>
                  <td className="px-6 py-4">
                    Compliance with legal and tax obligations
                  </td>
                </tr>
                <tr>
                  <td className="px-6 py-4">Usage Logs</td>
                  <td className="px-6 py-4">
                    Up to 90 days after account deletion
                  </td>
                  <td className="px-6 py-4">
                    Security monitoring and fraud prevention
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="space-y-6">
            <div>
              <h3 className="font-semibold mb-4">Requesting Deletion</h3>
              <p className="text-osce-ink-700 leading-relaxed">
                You can request deletion of your data at any time by contacting
                us at{" "}
                <a
                  href="mailto:privacy@fourintegers.com"
                  className="text-osce-accent hover:underline"
                >
                  privacy@fourintegers.com
                </a>{" "}
                or in app within settings. Upon receiving your request, we will:
              </p>
              <ul className="list-disc list-inside text-osce-ink-700 ml-6 mt-2">
                <li>
                  Immediately anonymize or soft-delete your data to ensure it is
                  no longer identifiable or accessible.
                </li>
                <li>
                  Complete final deletion of all non-essential data within 30
                  days, unless retention is required by law.
                </li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Anonymized Data</h3>
              <p className="text-osce-ink-700 leading-relaxed">
                We may retain anonymized data for up to 12 months for
                statistical analysis, service improvement, and compliance
                purposes. Anonymized data is no longer considered personal data
                under GDPR and cannot be linked back to an individual.
              </p>
            </div>
          </div>
        </section>

        <section id="changes-to-this-policy">
          <h2 className="text-osce-title font-semibold mb-6">
            11. Changes to This Policy
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We may update this policy periodically. Users are encouraged to
            review this policy regularly to stay informed about how we are
            protecting their data. Continued use of the platform after any
            changes constitutes acceptance of the updated policy.
          </p>
        </section>

        <section id="contact-information">
          <h2 className="text-osce-title font-semibold mb-6">
            12. Contact Information
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            For any privacy-related inquiries, please contact us at:
          </p>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6 mt-4">
            <li>
              Email:{" "}
              <a
                href="mailto:privacy@fourintegers.com"
                className="text-osce-accent hover:underline"
              >
                privacy@fourintegers.com
              </a>
            </li>
          </ul>
        </section>

        <section id="data-breach-notification">
          <h2 className="text-osce-title font-semibold mb-6">
            14. Data Breach Notification
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            In the event of a data breach that affects your personal data, we
            will notify you without undue delay and, where feasible, within 72
            hours of becoming aware of the breach. We will provide information
            about the nature of the breach, the data affected, and the measures
            we are taking to address it.
          </p>
        </section>

        <section id="third-party-data-sharing">
          <h2 className="text-osce-title font-semibold mb-6">
            15. Third-Party Data Sharing
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We may share your personal data with third parties in the following
            circumstances:
            <ul className="list-disc list-inside space-y-1 ml-6">
              <li>With your explicit consent</li>
              <li>To comply with legal obligations</li>
              <li>
                To protect the rights and safety of our users and the public
              </li>
              <li>
                With service providers who assist us in operating our platform
                and providing services to you
              </li>
            </ul>
          </p>
        </section>

        <section id="policy-review">
          <h2 className="text-osce-title font-semibold mb-6">16. Policy Review</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We will review this privacy policy regularly and update it as
            necessary to reflect changes in our practices or applicable laws. We
            encourage you to review this policy periodically for the latest
            information on our privacy practices.
          </p>
        </section>
      </div>
    </div>
  );
}
