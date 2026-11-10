import Link from "next/link";
import { REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { SiteButtonLink, SiteContainer } from "@/foundation/ui";
import { Rings } from "@/domains/marketing/home/Rings";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { CLOSING, HERO } from "@/domains/marketing/landingCopy";

const RINGS = ["top-1/2 h-[900px] w-[900px] -translate-y-1/2 border-white/10"];
const LINK = "font-landing-body text-sm font-medium text-white/85 underline-offset-4 hover:text-white hover:underline";

/** The deep-blue band that closes `/`; the card footer floats over its bottom edge. */
export function ClosingBand() {
  return (
    <section aria-labelledby="closing-title" className="relative overflow-hidden bg-site-deep pb-16 pt-16 text-center md:pb-52 md:pt-24">
      <Rings rings={RINGS} />
      <SiteContainer className="relative" innerClassName="flex flex-col items-center">
        <h2 id="closing-title" className="max-w-3xl text-balance font-landing-heading text-3xl font-bold leading-tight tracking-tight text-white md:text-5xl">{CLOSING.title}</h2>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <PartnerLink path={REGISTER_PATH} size="lg" variant="white">{HERO.cta}</PartnerLink>
          <SiteButtonLink href={`mailto:${SUPPORT_EMAIL}`} variant="ghost" size="lg">Contact us</SiteButtonLink>
        </div>
        <p className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-2">
          <Link href="/founders" className={LINK}>A message from our founders</Link>
          <Link href="/feedback" className={LINK}>Your feedback shapes our platform</Link>
        </p>
      </SiteContainer>
    </section>
  );
}
