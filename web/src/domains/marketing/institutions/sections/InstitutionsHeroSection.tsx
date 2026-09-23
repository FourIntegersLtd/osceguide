import Link from "next/link";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { InstitutionsHeroCircuitShowcase } from "../components/InstitutionsHeroCircuitShowcase";
import { DEMO_MAILTO } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";
import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";

export function InstitutionsHeroSection() {
  const type = institutionsLandingType;

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
        <h1 className={`${type.heroTitle} mx-auto max-w-[24ch] text-balance sm:max-w-[28ch]`}>
          <span className="block">Run training &amp; exam days</span>
          <span className="block">with virtual patients</span>
        </h1>
        <p className="mx-auto mt-6 max-w-[60ch] font-landing-body text-lg leading-8 text-landing-ink-muted sm:mt-7 sm:max-w-[68ch] sm:text-xl sm:leading-9">
          OSCE Guide helps institutions run OSCE training sessions and full exam
          days with virtual patients. Candidates get more time to practise,
          faculty spend less time on setup, and sessions stay on schedule.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row sm:flex-wrap">
          <a
            href={DEMO_MAILTO}
            className={`${type.ctaInk} w-full px-7 py-3.5 text-base sm:w-auto`}
          >
            Book a demo
          </a>
          <Link
            href={LOGIN_PATH}
            className={`${type.ctaSecondary} w-full px-7 py-3.5 text-center text-base sm:w-auto`}
          >
            Log in
          </Link>
        </div>

        <div className="mx-auto mt-10 max-w-[1000px] px-0 sm:mt-14 sm:px-2 lg:px-7">
          <InstitutionsHeroCircuitShowcase />
        </div>
      </div>
    </section>
  );
}
