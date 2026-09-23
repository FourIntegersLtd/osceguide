"use client";

import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";

import { HiOutlineBars3, HiOutlineXMark } from "react-icons/hi2";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import Logo from "@/foundation/ui/Logo";
import { useRouter } from "next/navigation";
import { ButtonLink } from "@/foundation/ui";
import { landingNavConfig } from "./landingConfig";
import { useLandingVariant } from "./LandingVariantContext";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";

export function LandingNav() {
  const partner = usePartnerContext();
  const router = useRouter();
  const { type, theme, accent } = useLandingVariant();
  const config = landingNavConfig;
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

  const handleLogin = () => {
    router.push(partner.href(LOGIN_PATH));
    closeMobileMenu();
  };

  const renderNavLink = (
    link: (typeof config.desktopLinks)[number],
    className: string,
  ) => {
    if (link.external) {
      return (
        <a
          key={link.href}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          className={className}
          onClick={closeMobileMenu}
        >
          {link.label}
        </a>
      );
    }

    return (
      <Link
        key={link.href}
        href={link.href}
        className={className}
        onClick={closeMobileMenu}
      >
        {link.label}
      </Link>
    );
  };

  const linkClass = type.navLink;

  return (
    <nav
      className={`${theme.navClassName} ${isMobileMenuOpen ? "bg-landing-canvas backdrop-blur-none" : ""}`}
    >
      <div className={`${type.sectionShell} relative z-50 flex h-[60px] items-center justify-between gap-5`}>
        <Logo variant="light" />

        <div className="hidden flex-wrap items-center gap-6 md:flex">
          {config.desktopLinks.map((link) => renderNavLink(link, linkClass))}
        </div>

        <div className="hidden items-center gap-3 md:flex">
          <button
            type="button"
            onClick={handleLogin}
            className={`${type.navLink} font-medium`}
          >
            Login ↗
          </button>
          <ButtonLink
            href="/institutions"
            variant="primary"
            size="md"
            className={`px-4 py-2.5 text-[13.5px] shadow-landing-cta ${accent.btn}`}
          >
            Institutions
          </ButtonLink>
        </div>

        <button
          type="button"
          className={`p-2 md:hidden ${linkClass}`}
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-expanded={isMobileMenuOpen}
          aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
        >
          {isMobileMenuOpen ? (
            <HiOutlineXMark className="h-6 w-6" />
          ) : (
            <HiOutlineBars3 className="h-6 w-6" />
          )}
        </button>
      </div>

      {isMobileMenuOpen && isMounted
        ? createPortal(
            <div
              data-b2c-landing-variant={
                theme.rootProps["data-b2c-landing-variant"]
              }
              data-b2c-landing-surface={
                theme.rootProps["data-b2c-landing-surface"]
              }
              className="fixed left-0 top-[60px] z-[55] flex h-[calc(100dvh-60px)] w-screen flex-col border-t border-landing-divider bg-landing-canvas px-5 py-4 sm:px-7 md:hidden"
              role="dialog"
              aria-modal="true"
              aria-label="Mobile navigation"
            >
              <div className="flex flex-col gap-3">
                {config.mobileLinks.map((link) =>
                  renderNavLink(link, `${linkClass} py-1.5`),
                )}
                <button
                  type="button"
                  onClick={handleLogin}
                  className={`${type.ctaInk} mt-2 w-full`}
                >
                  {config.mobileCtaLabel}
                </button>
              </div>
            </div>,
            document.body,
          )
        : null}
    </nav>
  );
}
