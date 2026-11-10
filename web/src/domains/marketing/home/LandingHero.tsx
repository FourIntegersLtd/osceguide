import { getImageProps } from "next/image";
import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { SiteButtonLink, SiteContainer } from "@/foundation/ui";
import { HERO_PHRASES, HeroPhrase } from "@/domains/marketing/home/HeroPhrase";
import { HeroProof } from "@/domains/marketing/home/HeroProof";
import { LANDING_SHOTS } from "@/domains/marketing/home/landingShots";
import { Rings } from "@/domains/marketing/home/Rings";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { HERO } from "@/domains/marketing/landingCopy";

const RINGS = [
  "hidden h-[1600px] w-[1600px] -top-[420px] border-white/10 md:block",
  "h-[760px] w-[760px] -top-[260px] border-white/[0.12] md:hidden",
  "h-[520px] w-[520px] -top-[120px] border-white/[0.14] md:h-[1200px] md:w-[1200px] md:-top-[220px] md:border-white/[0.12]",
  "hidden h-[840px] w-[840px] -top-10 border-white/[0.14] md:block",
];

/** A phone's status bar above the capture: time left, signal and battery right. Decorative. */
function PhoneStatusBar() {
  return (
    <div aria-hidden="true" className="flex h-[30px] items-center justify-between bg-white px-5 font-mono text-[11px] font-semibold text-site-ink md:hidden">
      <span>9:41</span>
      <svg width="30" height="11" viewBox="0 0 30 11" fill="currentColor">
        <rect x="0" y="7" width="3" height="4" rx="1" />
        <rect x="5" y="5" width="3" height="6" rx="1" />
        <rect x="10" y="2.5" width="3" height="8.5" rx="1" />
        <rect x="15" y="0" width="3" height="11" rx="1" />
        <rect x="21" y="0.5" width="8" height="10" rx="2.5" opacity="0.9" />
      </svg>
    </div>
  );
}

/** First screen: a deep-blue band, the headline and one button, and the learner dashboard in a device frame that hangs over the band's bottom edge. */
export function LandingHero() {
  // One <picture>, art-directed: a phone fetches only the phone capture and a laptop only the dashboard.
  const { props: { srcSet: desktopSrcSet } } = getImageProps({
    src: LANDING_SHOTS.marked.src,
    alt: "",
    width: LANDING_SHOTS.marked.width,
    height: LANDING_SHOTS.marked.height,
    sizes: "992px",
  });
  const { props: heroImg } = getImageProps({
    src: LANDING_SHOTS.markedMobile.src,
    alt: "",
    width: LANDING_SHOTS.markedMobile.width,
    height: LANDING_SHOTS.markedMobile.height,
    sizes: "260px",
    priority: true,
  });
  return (
    <header id="top" className="relative bg-site-deep pt-14 md:pt-24">
      <Rings rings={RINGS} />
      <SiteContainer className="relative" innerClassName="flex flex-col items-center text-center">
        <h1 className="max-w-[900px] font-landing-heading text-[clamp(1.75rem,8.5vw,4rem)] font-semibold leading-[1.08] tracking-tight text-white">
          <span className="sr-only">Your AI patient that {HERO_PHRASES[0]}</span>
          <span aria-hidden="true" className="block whitespace-nowrap">Your AI patient that</span>
          <HeroPhrase className="text-site-on-deep" />
        </h1>
        <p className="mt-5 max-w-[720px] text-[17px] leading-relaxed text-white/85 md:mt-7 md:text-[19px]">{HERO.lead}</p>
        <div className="mt-7 flex w-full flex-col gap-2.5 sm:w-auto sm:flex-row sm:gap-3.5 md:mt-9">
          <PartnerLink path={REGISTER_PATH} variant="white" size="lg">{HERO.cta}</PartnerLink>
          <SiteButtonLink href={`mailto:${SUPPORT_EMAIL}`} variant="ghost" size="lg">{HERO.contact}</SiteButtonLink>
        </div>
        <div className="mt-5 md:mt-[22px]"><HeroProof onDeep /></div>
        <figure className="relative z-10 -mb-[150px] mt-11 w-[280px] md:-mb-[260px] md:mt-[72px] md:w-full md:max-w-[1020px]">
          <div className="relative rounded-t-[40px] bg-site-device px-2.5 pt-2.5 [-webkit-mask-image:linear-gradient(to_bottom,black_55%,transparent)] [mask-image:linear-gradient(to_bottom,black_55%,transparent)] md:rounded-[22px] md:p-3.5 md:pb-[18px] md:shadow-2xl md:[-webkit-mask-image:none] md:[mask-image:none]">
            <div className="overflow-hidden rounded-t-[30px] bg-white md:h-[560px] md:rounded-xl">
              <PhoneStatusBar />
              <picture>
                <source media="(min-width: 768px)" sizes="992px" srcSet={desktopSrcSet} />
                <img {...heroImg} alt={LANDING_SHOTS.marked.alt} className="block h-auto w-full object-cover object-top md:h-full" />
              </picture>
            </div>
            <span aria-hidden="true" className="absolute left-1/2 top-4 h-[18px] w-[76px] -translate-x-1/2 rounded-full bg-site-device md:hidden" />
          </div>
          <div aria-hidden="true" className="-mx-3 hidden h-4 rounded-b-[18px] bg-site-device-base md:block" />
        </figure>
      </SiteContainer>
    </header>
  );
}
