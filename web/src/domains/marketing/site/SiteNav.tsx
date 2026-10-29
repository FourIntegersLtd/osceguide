"use client";

import Link from "next/link";
import { useState } from "react";
import { FiMenu, FiX } from "react-icons/fi";
import { LOGIN_PATH, REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { SiteButtonLink, SiteLogo } from "@/foundation/ui";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { LANDING_NAV_LINKS, SITE_NAV_LINKS } from "@/domains/marketing/site/siteLinks";

/**
 * The public site's nav. `landing` anchors to sections of `/` and offers
 * Institutions + Login; `site` links across pages and offers Login + Start free.
 * Under 960px the links fold into a disclosure menu.
 */
export function SiteNav({ variant = "site" }: { variant?: "landing" | "site" }) {
  const partner = usePartnerContext();
  const [open, setOpen] = useState(false);
  const links = variant === "landing" ? LANDING_NAV_LINKS : SITE_NAV_LINKS;
  const login = partner.href(LOGIN_PATH);
  const register = partner.href(REGISTER_PATH);

  const ctas =
    variant === "landing" ? (
      <>
        <SiteButtonLink href="/institutions" variant="line" size="sm">Institutions</SiteButtonLink>
        <SiteButtonLink href={login} variant="brand" size="sm">Login</SiteButtonLink>
      </>
    ) : (
      <>
        <SiteButtonLink href={login} variant="line" size="sm">Login</SiteButtonLink>
        <SiteButtonLink href={register} variant="brand" size="sm">Start free</SiteButtonLink>
      </>
    );

  return (
    <header className="sticky top-0 z-40 border-b border-site-line bg-site-ground/90 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-16 max-w-[1200px] items-center justify-between gap-4 px-4 sm:px-6">
        <SiteLogo />
        <ul className="hidden items-center gap-8 min-[960px]:flex">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="font-landing-body text-sm font-medium text-site-body transition-colors hover:text-site-brand">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="hidden items-center gap-2 min-[960px]:flex">{ctas}</div>
        <button
          type="button"
          aria-expanded={open}
          aria-controls="site-mobile-menu"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-site-rule text-site-ink min-[960px]:hidden"
        >
          {open ? <FiX aria-hidden /> : <FiMenu aria-hidden />}
        </button>
      </nav>
      {open && (
        <div id="site-mobile-menu" className="border-t border-site-line bg-site-ground px-4 pb-5 pt-3 min-[960px]:hidden">
          <ul className="flex flex-col">
            {links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="block py-3 font-landing-body text-base font-medium text-site-ink"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex gap-2">{ctas}</div>
        </div>
      )}
    </header>
  );
}
