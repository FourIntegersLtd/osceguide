"use client";

import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";

type ExamQuoteSectionProps = {
  quote: string;
  attribution: string;
};

export function ExamQuoteSection({ quote, attribution }: ExamQuoteSectionProps) {
  const { type } = useLandingVariant();

  return (
    <section
      className={`scroll-mt-20 py-16 sm:py-20 ${landingSectionSurfaces.founders}`}
    >
      <div className={`${type.sectionShell} max-w-osce-narrow`}>
        <figure className="relative m-0 overflow-hidden rounded-landing-panel border border-landing-warm bg-landing-card p-7 shadow-landing-panel sm:p-12">
          <span
            className="absolute right-5 top-2 select-none font-landing-heading text-[120px] leading-none text-landing-card-accent sm:right-8 sm:text-[160px]"
            aria-hidden
          >
            &rdquo;
          </span>
          <div className="relative">
            <blockquote className="font-landing-heading text-[clamp(1.25rem,5vw,1.75rem)] font-normal leading-[1.35] tracking-[-0.02em] text-osce-ink-900 sm:text-[clamp(1.375rem,2.4vw,1.75rem)]">
              {quote}
            </blockquote>
            <figcaption className="mt-6 flex items-center gap-3 border-t border-b2c-border-light pt-5 font-landing-body text-[11px] font-semibold uppercase tracking-[0.12em] text-osce-accent sm:text-xs sm:tracking-[0.14em]">
              <span className="h-px w-8 shrink-0 bg-osce-accent" aria-hidden />
              {attribution}
            </figcaption>
          </div>
        </figure>
      </div>
    </section>
  );
}
