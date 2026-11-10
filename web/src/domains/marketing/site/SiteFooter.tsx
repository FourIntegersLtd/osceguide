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

type Variant = "navy" | "light";

/** The class strings that differ between the navy footer and the light one, shell included. */
const FOOTER_TONE: Record<Variant, { shell: string; inner: string; heading: string; link: string; dim: string; social: string; rule: string }> = {
  navy: {
    shell: "bg-site-navy text-site-on-navy",
    inner: "py-14",
    heading: "text-site-on-navy-dim",
    link: "text-site-on-navy hover:text-white",
    dim: "text-site-on-navy-dim",
    social: "border-white/25 text-white hover:bg-white/10",
    rule: "border-white/15",
  },
  light: {
    shell: "pb-10 pt-16 md:pt-20",
    inner: "",
    heading: "text-site-muted",
    link: "text-site-body hover:text-site-brand",
    dim: "text-site-muted",
    social: "border-site-rule text-site-ink hover:bg-site-pale",
    rule: "border-site-line",
  },
};

function Column({ title, links, variant }: { title: string; links: readonly SiteLink[]; variant: Variant }): ReactNode {
  const tone = FOOTER_TONE[variant];
  return (
    <div>
      <h2 className={`font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] ${tone.heading}`}>{title}</h2>
      <ul className="mt-4 space-y-2.5">
        {links.map((l) => (
          <li key={l.href + l.label}>
            <Link href={l.href} className={`text-sm transition-colors hover:underline ${tone.link}`}>
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The navy footer shared by the legal pages; `light` is the plain one on the landing's page ground. */
export function SiteFooter({ variant = "navy" }: { variant?: Variant }) {
  const tone = FOOTER_TONE[variant];
  return (
    <footer className={`site-root font-landing-body ${tone.shell}`}>
      <SiteContainer innerClassName={tone.inner}>
        <div className="grid grid-cols-2 gap-x-6 gap-y-10 md:gap-10 lg:grid-cols-[1.4fr_1fr_1fr_1fr_1fr]">
          <div className="col-span-2 lg:col-span-1">
            <LogoLink onDark={variant === "navy"} />
            <address className={`mt-4 text-sm not-italic leading-relaxed ${tone.dim}`}>
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
                  className={`flex h-10 w-10 items-center justify-center rounded-full border transition-colors ${tone.social}`}
                >
                  <Icon aria-hidden />
                </a>
              ))}
            </div>
          </div>
          <Column title="Exams" links={FOOTER_EXAMS} variant={variant} />
          <Column title="Product" links={FOOTER_PRODUCT} variant={variant} />
          <Column title="Company" links={FOOTER_COMPANY} variant={variant} />
          <Column title="Legal" links={FOOTER_LEGAL} variant={variant} />
        </div>
        <p className={`mt-12 border-t pt-6 text-sm ${tone.rule} ${tone.dim}`}>
          &copy; {new Date().getFullYear()} Four Integers Ltd. All rights reserved.
        </p>
      </SiteContainer>
    </footer>
  );
}
