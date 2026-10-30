"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { FaBars, FaTimes } from "react-icons/fa";
import { Logo } from "@/foundation/ui";
import { B2BIconTooltipButton } from "@/domains/marketing/institutions/B2BIconTooltipButton";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import {
  DEMO_MAILTO,
  INSTITUTIONS_NAV,
} from "../institutionsLandingContent";
import {
  institutionsLandingTheme,
  institutionsLandingType,
} from "../institutionsLandingType";

export function InstitutionsLandingNav() {
  const type = institutionsLandingType;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobileMenuOpen]);

  return (
    <nav
      className={`${institutionsLandingTheme.navClassName} ${isMobileMenuOpen ? "bg-landing-canvas backdrop-blur-none" : ""}`}
    >
      <div
        className={`${type.sectionShell} relative z-50 flex h-[60px] items-center justify-between gap-5`}
      >
        <Link href="/" className="inline-flex shrink-0" aria-label="OSCE Guide home">
          <Logo variant="light" interactive={false} />
        </Link>

        <div className="hidden flex-wrap items-center gap-6 md:flex">
          {INSTITUTIONS_NAV.map((item) => (
            <Link key={item.href} href={item.href} className={type.navLink}>
              {item.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <Link href={LOGIN_PATH} className={`${type.navLink} font-medium`}>
            Log in ↗
          </Link>
          <a href={DEMO_MAILTO} className={type.ctaInk}>
            Book a demo
          </a>
        </div>

        <B2BIconTooltipButton
          label={isMobileMenuOpen ? "Close menu" : "Open menu"}
          showTooltip={false}
          variant="ghost"
          buttonClassName="p-2 text-landing-ink-body transition-colors hover:text-osce-ink-900 md:hidden"
          aria-expanded={isMobileMenuOpen}
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          {isMobileMenuOpen ? (
            <FaTimes className="h-6 w-6" aria-hidden />
          ) : (
            <FaBars className="h-6 w-6" aria-hidden />
          )}
        </B2BIconTooltipButton>
      </div>

      {isMobileMenuOpen && isMounted
        ? createPortal(
            <div
              data-b2c-landing-variant={
                institutionsLandingTheme.rootProps["data-b2c-landing-variant"]
              }
              data-b2c-landing-surface={
                institutionsLandingTheme.rootProps["data-b2c-landing-surface"]
              }
              className="fixed left-0 top-[60px] z-[55] flex h-[calc(100dvh-60px)] w-screen flex-col border-t border-landing-divider bg-landing-canvas px-5 py-4 sm:px-7 md:hidden"
              role="dialog"
              aria-modal="true"
              aria-label="Mobile navigation"
            >
              <div className="flex flex-col gap-3">
                {INSTITUTIONS_NAV.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`${type.navLink} py-1.5`}
                    onClick={closeMobileMenu}
                  >
                    {item.label}
                  </Link>
                ))}
                <Link
                  href={LOGIN_PATH}
                  className={`mt-2 inline-flex w-full justify-center ${type.ctaInk}`}
                  onClick={closeMobileMenu}
                >
                  Log in
                </Link>
              </div>
            </div>,
            document.body,
          )
        : null}
    </nav>
  );
}
