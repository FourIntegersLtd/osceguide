import type { Metadata } from "next";
import { SITE_URL } from "@/foundation/config/siteUrl";

export const metadata: Metadata = {
  title: "OSCE Guide - Cookie Policy",
  description:
    "Learn about how OSCE Guide uses cookies to enhance user experience and ensure platform functionality. Manage your cookie preferences.",
  alternates: {
    canonical: `${SITE_URL}/compliances/cookies-policy`,
  },
};

export default function CookiesPolicy() {
  return (
    <div className="py-12 px-6 sm:px-8 max-w-4xl mx-auto justify-center">
      <h1 className="text-osce-heading font-bold mb-8">Cookie Policy</h1>
      <p className="text-osce-body text-osce-ink-600 mb-4">
        Last Updated: December 31, 2024
      </p>

      <div className="space-y-16">
        <section>
          <h2 className="text-osce-title font-semibold mb-6">1. Introduction</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            At OSCE Guide, we use cookies to enhance the user experience and
            ensure the proper functioning of our platform. This Cookie Policy
            explains how we use cookies, what they do, and how users can manage
            their cookie preferences.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">2. What are Cookies?</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            Cookies are small files stored on your device that help websites
            remember certain information about your visit, such as login status,
            preferences, and usage patterns.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            3. Types of Cookies We Use
          </h2>
          <h3 className="text-osce-subheading font-semibold mb-4">
            3.1 Strictly Necessary Cookies
          </h3>
          <p className="text-osce-ink-700 leading-relaxed mb-4">
            These cookies are essential for the operation of the OSCE Guide
            platform. They include cookies that enable you to log in and
            maintain your session while using the app. Without these cookies,
            you will not be able to access the platform.
          </p>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              <strong>Authentication Cookies:</strong> These cookies are
              required to authenticate your login and manage your session on the
              app. By using the app, you consent to the use of these essential
              cookies.
            </li>
            <li>
              <strong>Session Cookies:</strong> These cookies maintain your
              session during your visit and ensure that you stay logged in as
              you navigate the platform.
            </li>
          </ul>

          <h3 className="text-osce-subheading font-semibold mb-4 mt-6">
            3.2 Analytics Cookies
          </h3>
          <p className="text-osce-ink-700 leading-relaxed mb-4">
            We use analytics cookies to understand how visitors interact with
            our platform. These cookies help us analyze usage patterns and
            improve our services. You can choose to accept or decline these
            cookies.
          </p>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              <strong>Usage Analytics:</strong> These cookies collect
              information about how you use our platform, including which pages
              you visit most frequently and any error messages you encounter.
            </li>
            <li>
              <strong>Performance Tracking:</strong> These cookies help us
              measure the performance of our platform and identify areas for
              improvement.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">4. Managing Cookies</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            While authentication cookies are strictly necessary and cannot be
            disabled, you have control over analytics cookies. You can manage
            your preferences through the cookie consent banner on the landing
            page.
          </p>
          <p className="text-osce-ink-700 leading-relaxed">
            If you choose to disable analytics cookies, you can still use the
            platform, but we will not be able to collect information about your
            usage patterns to improve our services.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">5. Why We Use Cookies</h2>
          <ul className="list-disc list-inside space-y-3 text-osce-ink-700 ml-6">
            <li>
              Authenticate Users: Ensure secure and correct access to the
              platform.
            </li>
            <li>
              Maintain Session Integrity: Keep users logged in throughout their
              visit to the app.
            </li>
            <li>
              Analytics: Collect data on how the platform is used to improve
              user experience and performance.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">
            6. Changes to This Policy
          </h2>
          <p className="text-osce-ink-700 leading-relaxed">
            We may update this Cookie Policy periodically to reflect changes in
            our use of cookies or regulations. Any updates will be communicated
            through the app and will be posted on this page.
          </p>
        </section>

        <section>
          <h2 className="text-osce-title font-semibold mb-6">7. Contact Us</h2>
          <p className="text-osce-ink-700 leading-relaxed">
            If you have any questions about this Cookie Policy, please contact
            us at:
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
      </div>
    </div>
  );
}
