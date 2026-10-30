import type { ReactNode } from "react";
import Link from "next/link";
import { LuArrowLeft } from "react-icons/lu";
import { LogoLink } from "@/foundation/ui";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { authHeader } from "@/foundation/ui/authTheme";

const FOOTER_LINKS = [
  { href: "/compliances/privacy-policy", label: "Privacy" },
  { href: "/compliances/terms-of-service", label: "Terms" },
  { href: "/compliances/cookies-policy", label: "Cookies" },
  { href: `mailto:${SUPPORT_EMAIL}`, label: "Help" },
] as const;

/**
 * Signing in, and everything next to it.
 *
 * Its own group because these pages belong to no workspace: a person on them
 * has no arm yet, and wrapping them in a surface shell would show them a
 * navigation they cannot use.
 *
 * The header is a logo with a way back to the marketing site: without it a
 * sign-in form has no brand on it and no exit.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="site-root site-auth flex min-h-screen flex-col font-landing-body antialiased">
      <header className={authHeader}>
        <div className="mx-auto flex min-h-16 max-w-[1120px] items-center justify-between px-4">
          <LogoLink />
          <Link href="/" className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-site-brand hover:text-site-brand-hover">
            <LuArrowLeft aria-hidden="true" />
            Back to the site
          </Link>
        </div>
      </header>
      <main className="flex flex-1 flex-col px-4 py-10 sm:py-14">{children}</main>
      <footer className="border-t border-site-line bg-site-card text-sm text-site-muted">
        <div className="mx-auto flex max-w-[1120px] flex-wrap items-center justify-between gap-3 px-4 py-5">
          <span>© OSCE Guide</span>
          <nav aria-label="Legal and help" className="flex flex-wrap gap-x-5 gap-y-2">
            {FOOTER_LINKS.map((link) => (
              <Link key={link.label} href={link.href} className="hover:text-site-brand">
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </div>
  );
}
