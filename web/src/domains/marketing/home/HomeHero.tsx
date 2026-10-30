import { FiArrowRight } from "react-icons/fi";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { SiteButtonLink } from "@/foundation/ui";
import { HERO_PHRASES, HeroPhrase } from "@/domains/marketing/home/HeroPhrase";
import { HeroIntro } from "@/domains/marketing/home/Blocks";
import { HeroProof } from "@/domains/marketing/home/HeroProof";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { PoweredBy } from "@/domains/marketing/home/PoweredBy";
import { ReportShowcase } from "@/domains/marketing/home/ReportShowcase";

const WAVE = [30, 55, 80, 45, 95, 60, 35, 75, 50, 90, 40, 70, 30, 85, 55, 65, 35, 80, 45, 60, 30, 70, 50, 85];

export function WaveBars({ heights, className = "h-14" }: { heights: readonly number[]; className?: string }) {
  return (
    <div className={`flex items-center justify-center gap-1 ${className}`} aria-hidden="true">
      {heights.map((h, i) => (
        <i
          key={i}
          className="site-wave-bar block w-1 rounded-full bg-site-brand"
          style={{ height: `${h}%`, animationDelay: `${(i % 7) * 0.12}s` }}
        />
      ))}
    </div>
  );
}

/** The landing's first screen: headline, CTAs, the sound of a consultation, a sample report, and who powers it. */
export function HomeHero() {
  return (
    <section id="top" className="px-4 pb-16 pt-14 text-center sm:px-6 sm:pt-20">
      <div className="mx-auto max-w-[1200px]">
        <HeroProof />
        <HeroIntro
          titleClass="text-[clamp(1.4rem,7.2vw,3.75rem)]"
          title={
            <>
              <span className="sr-only">Your AI patient that {HERO_PHRASES[0]}</span>
              <span aria-hidden="true" className="block whitespace-nowrap">
                Your AI patient that
              </span>
              <HeroPhrase />
            </>
          }
          lead="OSCE Guide transforms the way healthcare professionals prepare for their clinical simulation exams. Our Voice AI-powered platform simulates real patient interactions, helping you sharpen your clinical skills and enhance communication."
          ctas={
            <>
              <PartnerLink path={LOGIN_PATH} size="lg">
                Login <FiArrowRight aria-hidden />
              </PartnerLink>
              <SiteButtonLink href={`mailto:${SUPPORT_EMAIL}`} variant="line" size="lg">
                Contact us
              </SiteButtonLink>
            </>
          }
        />
        <WaveBars heights={WAVE} className="mx-auto mt-12 h-14 max-w-3xl" />
        <ReportShowcase />
        <PoweredBy />
      </div>
    </section>
  );
}
