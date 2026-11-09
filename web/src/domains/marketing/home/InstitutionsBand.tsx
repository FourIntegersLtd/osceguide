import { DEMO_MAILTO } from "@/foundation/support";
import { HiOutlineBuildingOffice2 } from "react-icons/hi2";
import { IconTile, SiteButtonLink } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { Shot } from "@/domains/marketing/home/Shot";
import { LANDING_SHOTS } from "@/domains/marketing/home/landingShots";
import { INSTITUTIONS } from "@/domains/marketing/landingCopy";

/** The one place programmes and employers appear on `/`: a pale band, text links only. */
export function InstitutionsBand() {
  return (
    <Section id="institutions" tone="pale" label="For institutions">
      <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <IconTile><HiOutlineBuildingOffice2 /></IconTile>
            <h2 className="text-balance font-landing-heading text-2xl font-bold leading-tight text-site-ink sm:text-3xl">{INSTITUTIONS.title}</h2>
          </div>
          <p className="mt-4 text-[17px] leading-relaxed text-site-body">{INSTITUTIONS.body}</p>
          <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2">
            <SiteButtonLink href="/institutions" variant="text" className="px-0 font-semibold text-site-brand">{INSTITUTIONS.link} →</SiteButtonLink>
            <SiteButtonLink href={DEMO_MAILTO} variant="text" className="px-0">{INSTITUTIONS.demo}</SiteButtonLink>
          </div>
        </div>
        <Shot shot={LANDING_SHOTS.institutions} sizes="(min-width: 1280px) 588px, (min-width: 1024px) 45vw, 100vw" />
      </div>
    </Section>
  );
}
