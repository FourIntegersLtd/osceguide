"use client";

import { B2CBandPill } from "@/foundation/ui/BandPill";
import type { ExamShowcaseVariant } from "./showcases/examShowcaseContent";
import { getHeroReportShowcaseContent } from "./showcases/heroReportShowcaseContent";

function ReportEyebrow({ children }: { children: string }) {
  return (
    <div className="font-landing-mono text-[8px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted sm:text-[10px]">
      {children}
    </div>
  );
}

function StationAvatar() {
  return (
    <div
      className="h-7 w-7 rounded-full bg-gradient-to-br from-osce-accent to-osce-accent-hover sm:h-10 sm:w-10"
      aria-hidden
    />
  );
}

const SIDE_CARD_BORDER =
  "rounded-[var(--landing-radius-card,0.5rem)] border border-landing-warm-strong bg-landing-card shadow-landing-showcase-side";

type HeroReportShowcaseProps = {
  variant?: ExamShowcaseVariant;
};

export function HeroReportShowcase({ variant = "sca" }: HeroReportShowcaseProps) {
  const content = getHeroReportShowcaseContent(variant);
  const { backLeft, backRight, front } = content;

  return (
    <div className="relative mx-auto w-full min-h-[300px] max-w-[1000px] px-1 pb-6 sm:min-h-[420px] sm:px-0 sm:pb-0">
      <div
        className={`pointer-events-none absolute bottom-6 left-[1%] top-2 w-[56%] ${SIDE_CARD_BORDER} p-3 rotate-[-8deg] sm:bottom-auto sm:left-[6%] sm:top-10 sm:h-[360px] sm:w-[50%] sm:max-w-[400px] sm:p-6 sm:rotate-[-9deg] lg:left-[4%] lg:top-[70px] lg:p-7`}
        aria-hidden
      >
        <ReportEyebrow>Station</ReportEyebrow>
        <div className="mt-2 hidden h-7 w-7 rounded-full bg-gradient-to-br from-osce-accent to-osce-accent-hover sm:mt-4 sm:block sm:h-[34px] sm:w-[34px]" />
        <div className="mt-1.5 font-landing-heading text-sm font-semibold leading-[1.15] tracking-[-0.025em] text-osce-ink-900 sm:mt-5 sm:text-[30px]">
          {backLeft.stationTitle}
        </div>
        <p className="mt-1 hidden font-landing-body text-xs leading-relaxed text-b2c-text-muted sm:mt-2 sm:block sm:text-[15px]">
          {backLeft.patientSummary}
        </p>
      </div>

      <div
        className={`pointer-events-none absolute bottom-6 right-[1%] top-1 flex w-[53%] flex-col justify-between ${SIDE_CARD_BORDER} p-3 rotate-[8deg] sm:bottom-auto sm:right-[6%] sm:top-8 sm:h-[380px] sm:w-[48%] sm:max-w-[380px] sm:p-6 sm:rotate-[8deg] lg:right-[4%] lg:top-14 lg:p-7`}
        aria-hidden
      >
        <div>
          <ReportEyebrow>Marks</ReportEyebrow>
          <div className="mt-1.5 text-right font-landing-heading text-xl font-medium leading-[1.1] text-osce-ink-900 sm:mt-2.5 sm:text-[30px]">
            {backRight.marks}
          </div>
        </div>
        <div className="flex items-baseline justify-between border-t border-landing-hairline pt-3 sm:pt-5">
          <span className="font-landing-body text-xs text-b2c-text-muted sm:text-base">
            Total
          </span>
          <span className="font-landing-heading text-lg font-semibold text-osce-ink-900 sm:text-[26px]">
            {backRight.totalPercent}
          </span>
        </div>
      </div>

      <div className="relative z-10 mx-auto w-[84%] max-w-[840px] overflow-hidden rounded-[var(--landing-radius-panel,10px)] border border-landing-warm bg-landing-card text-left shadow-landing-showcase sm:w-[90%] md:w-full">
        <div className="border-b border-landing-hairline px-3 py-2 sm:px-8 sm:py-6">
          <ReportEyebrow>Station</ReportEyebrow>
          <div className="mt-1 flex items-center gap-3 sm:mt-4 sm:gap-4">
            <div className="hidden sm:block">
              <StationAvatar />
            </div>
            <div className="min-w-0">
              <div className="font-landing-heading text-[13px] font-semibold leading-tight tracking-[-0.03em] text-osce-ink-900 sm:text-[clamp(1.625rem,3.4vw,2.5rem)] sm:leading-[1.1]">
                {front.stationTitle}
              </div>
              <p className="mt-0.5 font-landing-body text-[11px] leading-snug text-b2c-text-secondary sm:mt-1.5 sm:text-[clamp(0.9375rem,1.6vw,1.0625rem)] sm:leading-relaxed">
                {front.patientSummary} · {front.examMeta}
              </p>
            </div>
          </div>
        </div>

        <div className="px-3 py-2 sm:px-8 sm:pb-8 sm:pt-6">
          <div className="hidden items-baseline gap-4 border-b border-transparent pb-2.5 sm:flex">
            <div className="flex-1 font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
              Domain
            </div>
            <div className="w-[74px] shrink-0 text-right font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
              Marks
            </div>
            <div className="w-[168px] shrink-0 text-right font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
              Band
            </div>
          </div>

          <div className="divide-y divide-landing-hairline">
            {front.domains.map((row, index) => (
              <div
                key={row.domain}
                className={`flex flex-col gap-1 py-1.5 sm:flex-row sm:items-baseline sm:gap-4 sm:py-[18px] ${index > 1 ? "hidden sm:flex" : ""}`}
              >
                <div className="min-w-0 flex-1 font-landing-body text-[12px] font-medium leading-snug text-osce-ink-900 sm:text-[clamp(1rem,1.7vw,1.25rem)]">
                  {row.domain}
                </div>
                <div className="flex items-center justify-between gap-2 sm:contents">
                  <div className="font-landing-mono text-[12px] text-landing-ink-body sm:w-[74px] sm:shrink-0 sm:text-[clamp(0.9375rem,1.6vw,1.1875rem)] sm:text-right">
                    {row.marks}
                  </div>
                  <div className="sm:w-[168px] sm:shrink-0 sm:text-right">
                    <B2CBandPill
                      variant={row.variant}
                      className="max-sm:px-1.5 max-sm:py-1 max-sm:text-[8px]"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-1.5 flex items-baseline justify-between gap-4 border-t border-landing-warm pt-1.5 sm:mt-5 sm:gap-5 sm:pt-5">
            <span className="font-landing-body text-[12px] text-b2c-text-secondary sm:text-[clamp(1rem,1.7vw,1.1875rem)]">
              Total
            </span>
            <span className="font-landing-heading text-lg font-semibold tracking-[-0.03em] text-osce-ink-900 sm:text-[clamp(1.75rem,3.6vw,2.625rem)]">
              {front.total}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
