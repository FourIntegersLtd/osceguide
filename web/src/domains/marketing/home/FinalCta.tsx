import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { DEMO_MAILTO } from "@/foundation/support";
import { SiteButtonLink } from "@/foundation/ui";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { Section } from "@/domains/marketing/home/Section";
import { FINAL, HERO } from "@/domains/marketing/landingCopy";

/** The page's one navy band. */
export function FinalCta() {
  return (
    <Section tone="navy" label="Get started">
      <div className="max-w-2xl">
        <h2 className="text-balance font-landing-heading text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl">{FINAL.title}</h2>
        <p className="mt-4 text-lg text-site-on-navy">{FINAL.sub}</p>
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <PartnerLink path={REGISTER_PATH} variant="white" size="lg">{HERO.cta}</PartnerLink>
          <SiteButtonLink
            href={DEMO_MAILTO}
            variant="text"
            size="lg"
            className="px-0 text-white hover:text-white"
          >
            {FINAL.demo}
          </SiteButtonLink>
        </div>
      </div>
    </Section>
  );
}
