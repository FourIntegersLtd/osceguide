"use client";

import { HiOutlineArrowRight } from "react-icons/hi2";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";
import { HeroPoweredByStrip } from "./HeroPoweredByStrip";
import { HeroReportShowcase } from "./HeroReportShowcase";
import { HeroSocialProof } from "./HeroSocialProof";
import type { ExamKey } from "./landingExams";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import { LOGIN_PATH, REGISTER_PATH } from "@/domains/marketing/support/partnerConstants";

type ExamLandingHeroProps = {
  appType: ExamKey;
  title: ReactNode;
  lead: string;
  primaryCtaLabel?: string;
  /** Anchor for social proof link. Use `#testimonials` when the page includes that section. */
  testimonialsHref?: string;
};

export function ExamLandingHero({
  appType,
  title,
  lead,
  primaryCtaLabel = "Register",
  testimonialsHref = "/#testimonials",
}: ExamLandingHeroProps) {
  const { type } = useLandingVariant();
  const partner = usePartnerContext();
  const registerHref = partner.href(REGISTER_PATH, appType);
  const loginHref = partner.href(LOGIN_PATH, appType);

  return (
    <section
      className={`relative flex flex-col items-center pb-0 pt-14 sm:pt-16 ${landingSectionSurfaces.hero}`}
    >
      {/* Sky bloom behind the headline — decorative, no layout impact. */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-[640px] bg-[radial-gradient(ellipse_at_50%_-15%,var(--landing-bloom-soft,transparent)_0%,transparent_60%)]"
        aria-hidden
      />

      <div className={`${type.sectionShell} relative text-center`}>
        <HeroSocialProof testimonialsHref={testimonialsHref} />

        <h1
          className={`${type.heroTitle} mx-auto mt-6 w-full max-w-[min(100%,32ch)] text-balance sm:max-w-[28ch]`}
        >
          {title}
        </h1>

        <p className="mx-auto mt-6 max-w-[60ch] font-landing-body text-lg leading-8 text-landing-ink-muted sm:mt-7 sm:max-w-[68ch] sm:text-xl sm:leading-9">
          {lead}
        </p>

        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row sm:flex-wrap">
          <Link
            href={registerHref}
            className={`${type.ctaInk} group w-full max-w-sm gap-2 px-7 py-3.5 text-base sm:w-auto sm:max-w-none`}
          >
            {primaryCtaLabel}
            <HiOutlineArrowRight className="transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href={loginHref}
            className={`${type.ctaSecondary} w-full max-w-sm px-7 py-3.5 text-center text-base sm:w-auto sm:max-w-none`}
          >
            Log in
          </Link>
        </div>

        <div className="mx-auto mt-10 w-full max-w-[1000px] px-0 sm:mt-14 sm:px-2 lg:px-7">
          <HeroReportShowcase variant={appType} />
        </div>

        <div className="mx-auto max-w-[1180px] px-0 pb-10 pt-8 sm:pb-14 sm:pt-11">
          <HeroPoweredByStrip centered />
        </div>
      </div>
    </section>
  );
}
