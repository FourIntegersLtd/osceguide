import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { SiteButtonLink } from "@/foundation/ui";
import { HERO_PHRASES, HeroPhrase } from "@/domains/marketing/home/HeroPhrase";
import { HeroClip } from "@/domains/marketing/home/HeroClip";
import { HeroProof } from "@/domains/marketing/home/HeroProof";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { HERO } from "@/domains/marketing/landingCopy";

/** First screen: what it is, one button; the clip beside it. */
export function LandingHero() {
  return (
    <section id="top" className="px-4 pb-20 pt-12 sm:px-5 sm:pb-28 sm:pt-20">
      <div className="mx-auto grid max-w-[1280px] items-center gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-14">
        <div className="min-w-0">
          <h1 className="font-landing-heading text-[clamp(1.75rem,4.6vw,3.25rem)] font-bold leading-[1.1] tracking-tight text-site-ink">
            <span className="sr-only">Your AI patient that {HERO_PHRASES[0]}</span>
            <span aria-hidden="true" className="block whitespace-nowrap">Your AI patient that</span>
            <HeroPhrase />
          </h1>
          <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-site-body sm:text-lg">{HERO.lead}</p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
            <PartnerLink path={REGISTER_PATH} size="lg">{HERO.cta}</PartnerLink>
            <SiteButtonLink href={`mailto:${SUPPORT_EMAIL}`} variant="text" size="lg" className="px-0">{HERO.contact}</SiteButtonLink>
          </div>
          <div className="mt-8"><HeroProof align="start" /></div>
        </div>
        <HeroClip />
      </div>
    </section>
  );
}
