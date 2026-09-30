"use client";

import { usePartnerContext } from "@/domains/marketing/support/usePartnerContext";

import { HiOutlineArrowRight } from "react-icons/hi2";
import { useRouter } from "next/navigation";
import { HeroAnimatedPhrase } from "./HeroAnimatedPhrase";
import { HeroPoweredByStrip } from "./HeroPoweredByStrip";
import { HeroReportShowcase } from "./HeroReportShowcase";
import { HeroSocialProof } from "./HeroSocialProof";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";

export function ClassicLandingHero() {
  const partner = usePartnerContext();
  const router = useRouter();
  const { type } = useLandingVariant();

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
        <HeroSocialProof />

        <h1
          className={`${type.heroTitle} mx-auto mt-7 max-w-[24ch] text-balance sm:mt-8 sm:max-w-[28ch]`}
        >
          <span className="block">Your AI patient that</span>
          <span className="block">
            <HeroAnimatedPhrase variant="base" />
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-[60ch] font-landing-body text-lg leading-8 text-landing-ink-muted sm:mt-7 sm:max-w-[68ch] sm:text-xl sm:leading-9">
          OSCE Guide transforms the way healthcare professionals prepare for
          their clinical simulation exams. Our Voice AI-powered platform
          simulates real patient interactions, helping you sharpen your clinical
          skills and enhance communication.
        </p>

        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row sm:flex-wrap">
          <button
            type="button"
            onClick={() => router.push(partner.href(LOGIN_PATH))}
            className={`${type.ctaInk} group w-full gap-2 px-7 py-3.5 text-base sm:w-auto`}
          >
            Login
            <HiOutlineArrowRight className="transition-transform group-hover:translate-x-0.5" />
          </button>
          <a
            href="mailto:hello@fourintegers.com"
            className={`${type.ctaSecondary} w-full px-7 py-3.5 text-center text-base sm:w-auto`}
          >
            Contact us
          </a>
        </div>

        <div className="mx-auto mt-10 w-full max-w-[1000px] px-0 sm:mt-14 sm:px-2 lg:px-7">
          <HeroReportShowcase />
        </div>

        <div className="mx-auto max-w-[1180px] px-0 pb-12 pt-10 sm:pb-14 sm:pt-11">
          <HeroPoweredByStrip centered />
        </div>
      </div>
    </section>
  );
}
