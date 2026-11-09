"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { FiMenu, FiX } from "react-icons/fi";
import { LOGIN_PATH, REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { useMediaQuery } from "@/foundation/hooks";
import { SiteButtonLink, LogoLink, SiteContainer } from "@/foundation/ui";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { LANDING_NAV_LINKS, SITE_NAV_LINKS, type SiteLink } from "@/domains/marketing/site/siteLinks";
import type { ExamKey } from "@/domains/marketing/landingExams";

/**
 * The public site's nav. `landing` anchors to sections of `/` and offers
 * Login + Start free; `site` links across pages and offers Login + Start free.
 * Under 960px the links fold into a disclosure menu. `exam` keeps an exam page's
 * attribution on Login and Start free; `links` replaces the centre links (an
 * institutions page anchors to its own sections).
 */
export function SiteNav({ variant = "site", exam, links: custom }: { variant?: "landing" | "site"; exam?: ExamKey; links?: readonly SiteLink[] }) {
  const partner = usePartnerContext();
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const menuClose = useRef<HTMLButtonElement>(null);
  const links = custom ?? (variant === "landing" ? LANDING_NAV_LINKS : SITE_NAV_LINKS);
  const login = partner.href(LOGIN_PATH, exam);
  const register = partner.href(REGISTER_PATH, exam);

  const ctas =
    variant === "landing" ? (
      <>
        <SiteButtonLink href={login} variant="text" size="sm">Login</SiteButtonLink>
        <SiteButtonLink href="/institutions" variant="line" size="sm">Institutions</SiteButtonLink>
        <SiteButtonLink href={register} variant="brand" size="sm">Start free</SiteButtonLink>
      </>
    ) : (
      <>
        <SiteButtonLink href={login} variant="line" size="sm">Login</SiteButtonLink>
        <SiteButtonLink href={register} variant="brand" size="sm">Start free</SiteButtonLink>
      </>
    );

  const close = () => {
    setOpen(false);
    toggle.current?.focus();
  };
  // Widening past the breakpoint closes the menu.
  const wideNav = useMediaQuery("(min-width: 960px)");
  if (wideNav && open) setOpen(false);

  // While the menu is open: the page behind does not scroll, Escape closes, a link click closes, and Tab stays inside.
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    menuClose.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close();
        return;
      }
      if (e.key !== "Tab" || !menu.current) return;
      const items = menu.current.querySelectorAll<HTMLElement>("a[href], button:not([disabled])");
      const first = items[0];
      const last = items[items.length - 1];
      if (!first || !last) return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      if (e.target instanceof Element && e.target.closest("a")) setOpen(false);
    };
    const panel = menu.current;
    panel?.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      panel?.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- close only touches refs and a state setter

  return (
    <>
    <header className="sticky top-0 z-40 border-b border-site-line bg-site-ground/90 backdrop-blur">
      <SiteContainer innerClassName="flex h-16 items-center justify-between gap-4">
      <nav aria-label="Main" className="contents">
        <LogoLink />
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
          ref={toggle}
          type="button"
          aria-expanded={open}
          aria-controls="site-mobile-menu"
          aria-label="Open menu"
          onClick={() => setOpen(true)}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-site-rule text-site-ink min-[960px]:hidden"
        >
          <FiMenu aria-hidden />
        </button>
      </nav>
      </SiteContainer>
    </header>
    {open && (
      <div
        ref={menu}
        id="site-mobile-menu"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
        className="site-menu fixed inset-0 z-50 flex h-dvh w-full flex-col overflow-y-auto bg-site-ground min-[960px]:hidden"
      >
        <div className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-site-line px-4 sm:px-6">
          <LogoLink />
          <button
            ref={menuClose}
            type="button"
            aria-label="Close menu"
            onClick={close}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-site-rule text-site-ink"
          >
            <FiX aria-hidden />
          </button>
        </div>
        <ul className="flex flex-1 flex-col px-4 py-4 sm:px-6">
          {links.map((l) => (
            <li key={l.href} className="border-b border-site-line">
              <Link href={l.href} className="flex min-h-14 items-center font-landing-heading text-2xl font-bold text-site-ink">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="flex shrink-0 flex-col gap-3 px-4 pb-8 pt-4 sm:px-6 [&>a]:min-h-12 [&>a]:w-full">
          {ctas}
        </div>
      </div>
    )}
    </>
  );
}
