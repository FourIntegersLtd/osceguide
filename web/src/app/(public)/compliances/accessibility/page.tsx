import type { Metadata } from "next";
import { SITE_URL } from "@/foundation/config/siteUrl";
import { SUPPORT_EMAIL } from "@/capabilities/account/settings/PlanPicker";

export const metadata: Metadata = {
  title: "OSCE Guide - Accessibility Statement",
  description:
    "How accessible OSCE Guide is, what we know does not yet meet WCAG 2.2 AA, and how to tell us about a barrier.",
  alternates: {
    canonical: `${SITE_URL}/compliances/accessibility`,
  },
};

/**
 * The accessibility statement (E-15).
 *
 * Follows the shape of the GOV.UK model statement, which is what UK public
 * bodies buying from us check against. Every claim here must stay true: it
 * says what is checked automatically, that no full audit has been done, and
 * the gaps we know of. Update "Last reviewed" whenever the substance changes.
 */
export default function AccessibilityStatement() {
  return (
    <div className="mx-auto max-w-4xl py-12">
      <h1 className="mb-8 text-osce-heading font-bold">Accessibility statement</h1>

      <div className="space-y-12 text-osce-body leading-relaxed text-osce-ink-700">
        <p className="text-osce-ink-600">Last reviewed: 29 September 2026</p>

        <section className="space-y-4">
          <p>
            This statement covers osceguide.com: the practice app for candidates, the workspace
            institutions use to run sittings and review results, and the public site. We want as
            many people as possible to be able to use it. We are working towards everyone being
            able to:
          </p>
          <ul className="ml-6 list-disc space-y-2">
            <li>move through every page and form using a keyboard alone</li>
            <li>use the site with a screen reader and have form fields announced by name</li>
            <li>zoom text up to 200% without losing content</li>
            <li>
              take timed practice stations with extra time, which you can turn on under Settings,
              Preferences
            </li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-osce-title font-semibold">How accessible this website is</h2>
          <p>
            We aim to meet the Web Content Accessibility Guidelines (WCAG) version 2.2 at level
            AA. The site is <strong>partially compliant</strong>: we have not yet had it audited
            against the standard, and we know of the gaps listed below.
          </p>
          <p>Known gaps:</p>
          <ul className="ml-6 list-disc space-y-2">
            <li>Podcast episodes do not have transcripts.</li>
            <li>Slide deck videos do not have captions.</li>
            <li>
              Consultation stations are spoken conversations with a simulated patient. They need
              a microphone and speech, and there is no text-only way to take one.
            </li>
            <li>
              Some older screens, particularly in the station authoring tools, have not been
              checked with a screen reader.
            </li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-osce-title font-semibold">Feedback and contact information</h2>
          <p>
            If you find a barrier, or need something in a different format, email{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="font-medium text-osce-accent hover:text-osce-accent-hover">
              {SUPPORT_EMAIL}
            </a>
            . Tell us the page and what you were trying to do, and we will get back to you.
          </p>
          <p>
            If you sit exams through an institution, they can also arrange adjustments such as
            extra time for a sitting.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-osce-title font-semibold">Enforcement procedure</h2>
          <p>
            The Equality and Human Rights Commission (EHRC) is responsible for enforcing the UK
            accessibility regulations. If you are not happy with how we respond to your
            complaint, contact the{" "}
            <a
              href="https://www.equalityadvisoryservice.com/"
              className="font-medium text-osce-accent hover:text-osce-accent-hover"
            >
              Equality Advisory and Support Service (EASS)
            </a>
            .
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-osce-title font-semibold">How we test</h2>
          <p>
            Every change to the site is checked automatically against the jsx-a11y accessibility
            rules, which catch problems such as form fields without labels, images without text
            alternatives and controls that cannot be reached by keyboard. A change that breaks one
            of these rules cannot be released.
          </p>
          <p>
            Automated checks find only some problems. A full manual audit against WCAG 2.2 AA,
            including screen reader and keyboard testing of every journey, has not been done yet.
            We will update this statement when it has.
          </p>
        </section>
      </div>
    </div>
  );
}
