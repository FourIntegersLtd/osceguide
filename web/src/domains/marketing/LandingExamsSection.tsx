"use client";

import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { LANDING_EXAMS, useExamNavigation } from "./landingExams";
import { useLandingVariant } from "./LandingVariantContext";

export function LandingExamsSection() {
  const { type } = useLandingVariant();
  const { handleExamClick } = useExamNavigation();

  return (
    <section
      id="exams"
      className={`scroll-mt-20 ${landingSectionSurfaces.exams} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <div className="max-w-[56ch]">
          <h2 className={type.sectionTitle}>Choose your exam</h2>
          <p className={type.sectionSubtitle}>
            Select your exam pathway and start practicing with our AI-powered
            simulations
          </p>
        </div>

        <div className="mt-8 flex max-w-osce-narrow flex-col gap-3.5">
          {LANDING_EXAMS.map((exam) => (
            <button
              key={exam.key}
              type="button"
              onClick={() => handleExamClick(exam.key)}
              className="group flex w-full items-center justify-between gap-4 rounded-landing-card border border-landing-warm bg-landing-card px-5 py-4 text-left shadow-landing-card transition-[border-color,box-shadow] hover:border-osce-accent hover:shadow-landing-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas sm:gap-6 sm:px-7 sm:py-[22px]"
            >
              <div className="min-w-0">
                <h3 className="font-landing-heading text-[17px] font-semibold leading-[1.3] tracking-[-0.02em] text-osce-ink-900 sm:text-[19px]">
                  {exam.title}
                </h3>
                <p className={`mt-2 max-w-[52ch] ${type.itemBody}`}>
                  {exam.description}
                </p>
              </div>
              <span
                className={`shrink-0 font-landing-body text-sm font-medium text-osce-accent transition-colors group-hover:text-osce-accent-hover`}
                aria-hidden
              >
                →
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
