import Link from "next/link";
import type { ReactNode } from "react";
import { FaFacebook, FaLinkedin } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";
import { LogoLink, SiteContainer } from "@/foundation/ui";
import { FOOTER_COMPANY, FOOTER_EXAMS, FOOTER_LEGAL, FOOTER_PRODUCT, type SiteLink } from "@/domains/marketing/site/siteLinks";

const SOCIAL = [
  { href: "https://x.com/osceguide", label: "OSCE Guide on X", Icon: FaXTwitter },
  { href: "https://www.linkedin.com/company/osce-guide/", label: "OSCE Guide on LinkedIn", Icon: FaLinkedin },
  { href: "https://www.facebook.com/osceguide", label: "OSCE Guide on Facebook", Icon: FaFacebook },
] as const;

function Column({ title, links }: { title: string; links: readonly SiteLink[] }): ReactNode {
  return (
    <div>
      <h2 className="font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-on-navy-dim">{title}</h2>
      <ul className="mt-4 space-y-2.5">
        {links.map((l) => (
          <li key={l.href + l.label}>
            <Link href={l.href} className="text-sm text-site-on-navy transition-colors hover:text-white hover:underline">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The navy footer shared by the landing and the legal pages. */
export function SiteFooter() {
  return (
    <footer className="site-root bg-site-navy font-landing-body text-site-on-navy">
      <SiteContainer innerClassName="py-14">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1fr]">
          <div>
            <LogoLink onDark />
            <address className="mt-4 text-sm not-italic leading-relaxed text-site-on-navy-dim">
              82a James Carter Road<br />Mildenhall, IP28 7DE<br />England, UK
            </address>
            <div className="mt-5 flex gap-2">
              {SOCIAL.map(({ href, label, Icon }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-white/25 text-white transition-colors hover:bg-white/10"
                >
                  <Icon aria-hidden />
                </a>
              ))}
            </div>
          </div>
          <Column title="Exams" links={FOOTER_EXAMS} />
          <Column title="Product" links={FOOTER_PRODUCT} />
          <Column title="Company" links={FOOTER_COMPANY} />
          <Column title="Legal" links={FOOTER_LEGAL} />
        </div>
        <p className="mt-12 border-t border-white/15 pt-6 text-sm text-site-on-navy-dim">
          &copy; {new Date().getFullYear()} Four Integers Ltd. All rights reserved.
        </p>
      </SiteContainer>
    </footer>
  );
}
