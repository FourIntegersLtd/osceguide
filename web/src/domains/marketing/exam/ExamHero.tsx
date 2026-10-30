import type { ReactNode } from "react";
import { FiArrowRight } from "react-icons/fi";
import { LOGIN_PATH, REGISTER_PATH } from "@/foundation/attribution/partnerConstants";
import { B2CBandPill } from "@/foundation/ui/BandPill";
import { HeroIntro } from "@/domains/marketing/home/Blocks";
import { HeroProof } from "@/domains/marketing/home/HeroProof";
import { PartnerLink } from "@/domains/marketing/home/PartnerLink";
import { PartnerWelcomeBanner } from "@/domains/marketing/PartnerWelcomeBanner";
import { PoweredBy } from "@/domains/marketing/home/PoweredBy";
import type { ExamKey } from "@/domains/marketing/landingExams";
import { getHeroReportShowcaseContent } from "@/domains/marketing/showcases/heroReportShowcaseContent";

const LABEL = "font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-muted";
const SIDE = "rounded-2xl border border-site-line bg-site-card p-5";

/** The sample report under the headline: the station beside the marked station, beside its marks. */
function ExamReport({ exam }: { exam: ExamKey }) {
  const { backLeft, backRight, front } = getHeroReportShowcaseContent(exam);
  return (
    <div className="mx-auto mt-12 grid max-w-5xl gap-4 text-left lg:grid-cols-[1fr_1.9fr_1fr] lg:items-center">
      <div aria-hidden="true" className={`${SIDE} order-2 lg:order-1`}>
        <div className={LABEL}>Station</div>
        <div className="mt-3 h-9 w-9 rounded-full bg-site-brand" />
        <div className="mt-4 font-landing-heading text-xl font-bold text-site-ink">{backLeft.stationTitle}</div>
        <p className="mt-1 text-sm text-site-muted">{backLeft.patientSummary}</p>
      </div>

      <div className="order-1 overflow-hidden rounded-2xl border border-site-line bg-site-card shadow-sm lg:order-2">
        <div className="border-b border-site-line p-5 sm:p-6">
          <div className={LABEL}>Station</div>
          <div className="mt-3 flex items-center gap-3">
            <div aria-hidden="true" className="hidden h-10 w-10 shrink-0 rounded-full bg-site-brand sm:block" />
            <div className="min-w-0">
              <div className="font-landing-heading text-xl font-bold leading-tight text-site-ink sm:text-2xl">{front.stationTitle}</div>
              <p className="mt-1 text-sm text-site-body">
                {front.patientSummary} · {front.examMeta}
              </p>
            </div>
          </div>
        </div>
        <div className="p-5 sm:p-6">
          <div className={`hidden gap-4 pb-2 sm:flex ${LABEL}`}>
            <div className="flex-1">Domain</div>
            <div className="w-16 text-right">Marks</div>
            <div className="w-36 text-right">Band</div>
          </div>
          <div className="divide-y divide-site-line">
            {front.domains.map((row) => (
              <div key={row.domain} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:gap-4">
                <div className="min-w-0 flex-1 font-medium text-site-ink">{row.domain}</div>
                <div className="flex items-center justify-between gap-2 sm:contents">
                  <div className="font-landing-mono text-site-body sm:w-16 sm:text-right">{row.marks}</div>
                  <div className="sm:w-36 sm:text-right">
                    <B2CBandPill variant={row.variant} />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-baseline justify-between gap-4 border-t border-site-line pt-4">
            <span className="text-site-body">Total</span>
            <span className="font-landing-heading text-3xl font-bold text-site-ink">{front.total}</span>
          </div>
        </div>
      </div>

      <div aria-hidden="true" className={`${SIDE} order-3 flex flex-col justify-between gap-6`}>
        <div>
          <div className={LABEL}>Marks</div>
          <div className="mt-3 font-landing-heading text-3xl font-bold text-site-ink">{backRight.marks}</div>
        </div>
        <div className="flex items-baseline justify-between border-t border-site-line pt-4">
          <span className="text-site-body">Total</span>
          <span className="font-landing-heading text-2xl font-bold text-site-ink">{backRight.totalPercent}</span>
        </div>
      </div>
    </div>
  );
}

type ExamHeroProps = {
  exam: ExamKey;
  title: ReactNode;
  lead: string;
  /** `#testimonials` when the page has that section; the landing's otherwise. */
  testimonialsHref?: string;
};

/** The first screen of an exam page: proof, headline, the two funnel links, a sample report and who powers it. */
export function ExamHero({ exam, title, lead, testimonialsHref = "/#testimonials" }: ExamHeroProps) {
  return (
    <section className="px-4 pb-16 pt-6 text-center sm:px-6 sm:pt-10">
      <div className="mx-auto max-w-[1200px]">
        <PartnerWelcomeBanner tone="site" className="mx-auto mb-10 max-w-3xl text-left" />
        <HeroProof testimonialsHref={testimonialsHref} />
        <HeroIntro
          title={title}
          lead={lead}
          ctas={
            <>
              <PartnerLink path={REGISTER_PATH} exam={exam} size="lg">
                Register <FiArrowRight aria-hidden />
              </PartnerLink>
              <PartnerLink path={LOGIN_PATH} exam={exam} variant="line" size="lg">
                Log in
              </PartnerLink>
            </>
          }
        />
        <ExamReport exam={exam} />
        <PoweredBy />
      </div>
    </section>
  );
}
