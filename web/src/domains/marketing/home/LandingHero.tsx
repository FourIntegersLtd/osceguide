import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { Eyebrow, SiteButtonLink } from "@/foundation/ui";
import { HeroClip } from "@/domains/marketing/home/HeroClip";
import { HeroProofLine } from "@/domains/marketing/home/HeroProofLine";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { HERO } from "@/domains/marketing/landingCopy";

/** First screen: what it is, who for, one button; the clip beside it. */
export function LandingHero() {
  return (
    <section id="top" className="px-4 pb-16 pt-12 sm:px-6 sm:pb-20 sm:pt-20">
      <div className="mx-auto grid max-w-[1200px] items-center gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-14">
        <div className="min-w-0">
          <Eyebrow>{HERO.eyebrow}</Eyebrow>
          <h1 className="mt-5 text-balance font-landing-heading text-[clamp(2rem,4.2vw,3rem)] font-bold leading-[1.1] tracking-tight text-site-ink">
            {HERO.title} <span className="text-site-muted">{HERO.titleTail}</span>
          </h1>
          <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-site-body">{HERO.lead}</p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
            <PartnerLink path={REGISTER_PATH} size="lg">{HERO.cta}</PartnerLink>
            <SiteButtonLink href="#features" variant="text" size="lg" className="px-0">{HERO.sample}</SiteButtonLink>
          </div>
          <HeroProofLine />
        </div>
        <HeroClip />
      </div>
    </section>
  );
}
