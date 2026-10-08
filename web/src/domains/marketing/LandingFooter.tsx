import { SUPPORT_EMAIL } from "@/foundation/support";
import { FaFacebook, FaLinkedin } from "react-icons/fa";
import Link from "next/link";
import { FaXTwitter } from "react-icons/fa6";
// One login for every product: the surface is chosen from memberships,
// not from which page you signed in on.
const B2B_LOGIN_ROUTE = "/login";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { cn } from "@/foundation/ui";

const SOCIAL_ICON_CLASS =
  "flex h-10 w-10 items-center justify-center rounded-[var(--landing-radius-card,0.5rem)] border border-[color:var(--landing-warm,#e2e8f0)] bg-landing-card text-[color:var(--landing-ink-body,#334155)] shadow-landing-card transition-all hover:scale-105 hover:border-osce-accent-light hover:bg-osce-accent-muted hover:text-osce-accent-hover";

const SOCIAL_ICON_BLUE_CLASS =
  "flex h-10 w-10 items-center justify-center rounded-lg border border-white/35 bg-white/15 text-white transition-all hover:scale-105 hover:border-white/60 hover:bg-white/25";

/** Path form of the exam landings; `sca.osceguide.com` rewrites to the same page. */
const FOOTER_EXAMS = [
  { key: "sca", label: "SCA (UK)" },
  { key: "plab", label: "PLAB 2 (UK)" },
  { key: "casc", label: "MRCPsych CASC" },
  { key: "ortho", label: "Orthopaedic ST3" },
] as const;

const FOOTER_LINK_CLASS =
  "text-sm text-landing-ink-muted transition-colors hover:text-osce-ink-900";

const FOOTER_LINK_BLUE_CLASS =
  "text-sm text-white/95 transition-colors hover:text-white underline-offset-2 hover:underline";

type LandingFooterProps = {
  className?: string;
  variant?: "default" | "blue";
  /** Prefix for home-page section anchors. Use `""` on the main landing (`/#faq` → `#faq`); use `"/"` on exam landings (`/#faq`). */
  sectionLinkPrefix?: "" | "/";
};

export function LandingFooter({
  className = "",
  variant = "default",
  sectionLinkPrefix = "",
}: LandingFooterProps) {
  const isBlue = variant === "blue";
  const faqHref = `${sectionLinkPrefix}#faq`;
  const socialClass = isBlue ? SOCIAL_ICON_BLUE_CLASS : SOCIAL_ICON_CLASS;
  const linkClass = isBlue ? FOOTER_LINK_BLUE_CLASS : FOOTER_LINK_CLASS;
  const headingClass = isBlue
    ? "text-xs font-semibold uppercase tracking-wider text-white"
    : "font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-b2c-text-muted";
  const bodyTextClass = isBlue
    ? "text-sm leading-relaxed text-white/95"
    : "text-sm leading-relaxed text-b2c-text-secondary";
  const copyrightClass = isBlue
    ? "text-center text-sm text-white/90"
    : "text-center text-sm text-b2c-text-secondary";

  return (
    <footer
      className={cn(
        isBlue
          ? "bg-gradient-to-br from-osce-accent via-[#1d4ed8] to-[#1e3a8a]"
          : landingSectionSurfaces.footer,
        className,
      )}
    >
      <div className="mx-auto w-full max-w-osce-page px-5 py-11 sm:px-7 sm:py-14">
        <div className="grid grid-cols-1 gap-12 sm:gap-16 lg:grid-cols-12 lg:gap-8">
          <div className="flex flex-col gap-6 lg:col-span-3">
            <div className="flex flex-col gap-3">
              <h4 className={headingClass}>Follow Us</h4>
              <div className="flex gap-3">
                <a
                  href="https://x.com/osceguide"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={socialClass}
                  aria-label="X (Twitter)"
                >
                  <FaXTwitter className="h-4 w-4" />
                </a>
                <a
                  href="https://www.linkedin.com/company/osce-guide/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={socialClass}
                  aria-label="LinkedIn"
                >
                  <FaLinkedin className="h-4 w-4" />
                </a>
                <a
                  href="https://facebook.com/osceguide"
                  target="_blank"
                  rel="noopener noreferrer"
                  className={socialClass}
                  aria-label="Facebook"
                >
                  <FaFacebook className="h-4 w-4" />
                </a>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <h4 className={headingClass}>Address</h4>
              <p className={bodyTextClass}>
                82a James Carter Road <br /> Mildenhall, IP28 7DE <br /> England,
                UK
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-2 lg:col-span-9 lg:grid-cols-4">
            <div>
              <h4 className={`mb-4 ${headingClass}`}>Exams</h4>
              <ul className="space-y-3">
                {FOOTER_EXAMS.map((exam) => (
                  <li key={exam.key}>
                    <Link href={`/exams/${exam.key}`} className={linkClass}>
                      {exam.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className={`mb-4 ${headingClass}`}>Institutions</h4>
              <ul className="space-y-3">
                <li>
                  <Link href="/institutions" className={linkClass}>
                    For universities & programmes
                  </Link>
                </li>
                <li>
                  <Link href={B2B_LOGIN_ROUTE} className={linkClass}>
                    Log in
                  </Link>
                </li>
                <li>
                  <a
                    href={`mailto:${SUPPORT_EMAIL}?subject=OSCE%20Guide%20Institutions%20Demo`}
                    className={linkClass}
                  >
                    Book a demo
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className={`mb-4 ${headingClass}`}>Resources</h4>
              <ul className="space-y-3">
                <li>
                  <Link href={faqHref} className={linkClass}>
                    FAQs
                  </Link>
                </li>
                <li>
                  <Link href="/blogs" className={linkClass}>
                    Blog
                  </Link>
                </li>
                <li>
                  <a href={`mailto:${SUPPORT_EMAIL}`} className={linkClass}>
                    Contact us
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className={`mb-4 ${headingClass}`}>Legal</h4>
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
                  <Link href="/compliances/accessibility" className={linkClass}>
                    Accessibility
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
