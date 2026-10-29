import Image from "next/image";
import { FiArrowRight } from "react-icons/fi";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { LOGIN_PATH } from "@/foundation/attribution/partnerConstants";
import { SiteButtonLink } from "@/foundation/ui";
import { HeroPhrase } from "@/domains/marketing/home/HeroPhrase";
import { HeroProof } from "@/domains/marketing/home/HeroProof";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
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
        <h1 className="mx-auto mt-6 max-w-4xl font-landing-heading text-[40px] font-bold leading-[1.08] tracking-tight text-site-ink sm:text-6xl">
          Your AI patient that <HeroPhrase />
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-site-body">
          OSCE Guide transforms the way healthcare professionals prepare for their clinical simulation exams. Our Voice AI-powered
          platform simulates real patient interactions, helping you sharpen your clinical skills and enhance communication.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <PartnerLink path={LOGIN_PATH} size="lg">
            Login <FiArrowRight aria-hidden />
          </PartnerLink>
          <SiteButtonLink href={`mailto:${SUPPORT_EMAIL}`} variant="line" size="lg">
            Contact us
          </SiteButtonLink>
        </div>
        <WaveBars heights={WAVE} className="mx-auto mt-12 h-14 max-w-3xl" />
        <ReportShowcase />
        <div className="mx-auto mt-12 flex max-w-3xl flex-wrap items-center justify-center gap-x-4 gap-y-3 text-sm text-site-muted">
          <b className="font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-faint">Powered by</b>
          <a
            href="https://deepgram.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg border border-site-line bg-white px-3 py-2"
          >
            <Image src="/images/deepgram_logo.png" alt="Deepgram" width={96} height={28} className="h-7 w-auto" />
          </a>
          <a
            href="https://aws.amazon.com/events/aws-innovate/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg border border-site-line bg-white px-3 py-2"
          >
            <Image src="/images/aws_logo.png" alt="AWS" width={64} height={34} className="h-7 w-auto" />
          </a>
          <span>Proud recipient of startup grants from industry leaders in AI and cloud computing</span>
        </div>
      </div>
    </section>
  );
}
