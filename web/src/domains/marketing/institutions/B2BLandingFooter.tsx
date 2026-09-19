import Link from "next/link";
import { FaFacebook, FaLinkedin } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";
import { LOGIN_PATH } from "@/domains/marketing/support/partnerConstants";
import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { b2bLinkMuted } from "@/foundation/ui/b2bTokens";

const DEMO_MAILTO =
  "mailto:hello@fourintegers.com?subject=OSCE%20Guide%20Institutions%20Demo";

const FOOTER_COLUMN_HEADING =
  "mb-4 text-osce-caption font-semibold uppercase tracking-wider text-b2b-accent";

const FOOTER_SIDEBAR_HEADING =
  "text-osce-caption font-semibold uppercase tracking-wider text-b2b-accent";

const FOOTER_LINK_CLASS = `${b2bLinkMuted} text-osce-meta`;

const SOCIAL_ICON_CLASS =
  "flex h-10 w-10 items-center justify-center rounded-lg border border-b2b-border bg-b2b-surface text-b2b-graphite transition-all hover:scale-105 hover:border-b2b-accent-border hover:bg-b2b-accent-bg hover:text-b2b-accent-hover";

type B2BLandingFooterProps = {
  className?: string;
  /** Prefix for on-page section anchors. Use `""` on `/b2b/institutions` (`#for`); use `"/b2b/institutions"` elsewhere. */
  sectionLinkPrefix?: "" | "/b2b/institutions";
  /** Marketing pages use the classic B2C landing footer palette. */
  variant?: "workspace" | "marketing";
};

/** B2B landing footer. Same structure as B2C `LandingFooter`. */
export function B2BLandingFooter({
  className = "",
  sectionLinkPrefix = "",
  variant = "workspace",
}: B2BLandingFooterProps) {
  const forHref = `${sectionLinkPrefix}#for`;
  const howHref = `${sectionLinkPrefix}#how`;
  const platformHref = `${sectionLinkPrefix}#platform`;
  const isMarketing = variant === "marketing";

  const headingClass = isMarketing
    ? "text-osce-caption font-semibold uppercase tracking-wider text-osce-accent"
    : FOOTER_SIDEBAR_HEADING;
  const linkClass = isMarketing
    ? "text-osce-meta text-landing-ink-muted transition-colors hover:text-osce-ink-900"
    : FOOTER_LINK_CLASS;
  const bodyTextClass = isMarketing
    ? "text-osce-meta leading-relaxed text-b2c-text-secondary"
    : "text-osce-meta leading-relaxed text-b2b-mid";
  const copyrightClass = isMarketing
    ? "text-center text-osce-meta text-b2c-text-secondary"
    : "text-center text-osce-meta text-b2b-mid";
  const staticTextClass = isMarketing
    ? "text-osce-meta text-b2c-text-secondary"
    : "text-osce-meta text-b2b-mid";
  const socialClass = isMarketing
    ? "flex h-10 w-10 items-center justify-center rounded-[var(--landing-radius-card,0.5rem)] border border-[color:var(--landing-warm,#e2e8f0)] bg-landing-card text-[color:var(--landing-ink-body,#334155)] shadow-landing-card transition-all hover:scale-105 hover:border-osce-accent-light hover:bg-osce-accent-muted hover:text-osce-accent-hover"
    : SOCIAL_ICON_CLASS;

  return (
    <footer
      className={`${
        isMarketing
          ? landingSectionSurfaces.footer
          : "border-t border-b2b-border bg-b2b-canvas"
      } ${className}`.trim()}
    >
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:py-16">
        <div className="grid grid-cols-1 gap-12 sm:gap-16 lg:grid-cols-12 lg:gap-8">
          <div className="flex flex-col gap-6 lg:col-span-3">
            <div className="flex flex-col gap-3">
              <h4 className={headingClass}>Follow us</h4>
              <div className="flex gap-3">
                <a
                  href="https://x.com/osceguide"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={socialClass}
                  aria-label="X (Twitter)"
                >
                  <FaXTwitter className="h-4 w-4" aria-hidden />
                </a>
                <a
                  href="https://www.linkedin.com/company/osce-guide/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={socialClass}
                  aria-label="LinkedIn"
                >
                  <FaLinkedin className="h-4 w-4" aria-hidden />
                </a>
                <a
                  href="https://facebook.com/osceguide"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={socialClass}
                  aria-label="Facebook"
                >
                  <FaFacebook className="h-4 w-4" aria-hidden />
                </a>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <h4 className={headingClass}>Address</h4>
              <p className={bodyTextClass}>
                82a James Carter Road
                <br />
                Mildenhall, IP28 7DE
                <br />
                England, UK
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-2 lg:col-span-9 lg:grid-cols-4">
            <div>
              <h4 className={isMarketing ? headingClass : FOOTER_COLUMN_HEADING}>
                Exams
              </h4>
              <ul className="space-y-3">
                <li>
                  <span className={staticTextClass}>SCA (UK)</span>
                </li>
                <li>
                  <span className={staticTextClass}>PLAB 2 (UK)</span>
                </li>
                <li>
                  <span className={staticTextClass}>Orthopaedic ST3</span>
                </li>
              </ul>
            </div>

            <div>
              <h4 className={isMarketing ? headingClass : FOOTER_COLUMN_HEADING}>
                Institutions
              </h4>
              <ul className="space-y-3">
                <li>
                  <Link href="/b2b/institutions" className={linkClass}>
                    For universities &amp; programmes
                  </Link>
                </li>
                <li>
                  <Link href={LOGIN_PATH} className={linkClass}>
                    Log in
                  </Link>
                </li>
                <li>
                  <a href={DEMO_MAILTO} className={linkClass}>
                    Book a demo
                  </a>
                </li>
                <li>
                  <Link href={LOGIN_PATH} className={linkClass}>
                    Partner workspace
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h4 className={isMarketing ? headingClass : FOOTER_COLUMN_HEADING}>
                Resources
              </h4>
              <ul className="space-y-3">
                <li>
                  <Link href={forHref} className={linkClass}>
                    Who it&apos;s for
                  </Link>
                </li>
                <li>
                  <Link href={howHref} className={linkClass}>
                    How it works
                  </Link>
                </li>
                <li>
                  <Link href={platformHref} className={linkClass}>
                    Platform
                  </Link>
                </li>
                <li>
                  <Link href="/#faq" className={linkClass}>
                    FAQs
                  </Link>
                </li>
                <li>
                  <Link href="/blogs" className={linkClass}>
                    Blog
                  </Link>
                </li>
                <li>
                  <a href="mailto:hello@fourintegers.com" className={linkClass}>
                    Contact us
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <h4 className={isMarketing ? headingClass : FOOTER_COLUMN_HEADING}>
                Legal
              </h4>
              <ul className="space-y-3">
                <li>
                  <Link href="/compliances/privacy-policy" className={linkClass}>
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="/compliances/cookies-policy" className={linkClass}>
                    Cookie Policy
                  </Link>
                </li>
                <li>
                  <Link href="/compliances/terms-of-service" className={linkClass}>
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link href="/compliances/legal-disclaimer" className={linkClass}>
                    Legal Disclaimer
                  </Link>
                </li>
                <li>
                  <Link href="/compliances/referrals" className={linkClass}>
                    Referral Policy
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-4 sm:mt-16">
          <p className={copyrightClass}>
            © {new Date().getFullYear()} Four Integers Ltd. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
