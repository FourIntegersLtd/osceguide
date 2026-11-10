import { DEMO_MAILTO } from "@/foundation/support";
import { HiOutlineBuildingOffice2 } from "react-icons/hi2";
import { IconTile, SiteButtonLink, SiteContainer } from "@/foundation/ui";
import { INSTITUTIONS } from "@/domains/marketing/landingCopy";

/** The one place programmes and employers appear on `/`: a one-line card, text links only. */
export function InstitutionsBand() {
  return (
    <section id="institutions" aria-label="For institutions" className="scroll-mt-16 py-6 md:py-10">
      <SiteContainer>
        <div className="flex flex-col gap-4 rounded-2xl border border-site-line bg-site-card p-5 md:flex-row md:items-center md:justify-between md:px-8 md:py-6">
          <div className="flex items-center gap-3">
            <IconTile><HiOutlineBuildingOffice2 /></IconTile>
            <h2 className="text-balance font-landing-heading text-lg font-bold leading-tight text-site-ink md:text-xl">{INSTITUTIONS.title}</h2>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <SiteButtonLink href="/institutions" variant="text" className="px-0 font-semibold text-site-brand">{INSTITUTIONS.link} &rarr;</SiteButtonLink>
            <SiteButtonLink href={DEMO_MAILTO} variant="text" className="px-0">{INSTITUTIONS.demo}</SiteButtonLink>
          </div>
        </div>
      </SiteContainer>
    </section>
  );
}
