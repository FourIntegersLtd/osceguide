import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsAboutSection() {
  const type = institutionsLandingType;

  return (
    <section className={`${landingSectionSurfaces.founders} ${type.sectionPadding}`}>
      <div className={`${type.sectionShell} max-w-osce-narrow`}>
        <p className={type.eyebrow}>About us</p>
        <h2 className="mt-5 font-landing-heading text-[clamp(1.5rem,2.8vw,2rem)] font-semibold leading-[1.2] tracking-[-0.025em] text-osce-ink-900">
          Built by clinicians who have run these exams
        </h2>
        <div className="mt-6 flex flex-col gap-[18px]">
          <p className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
            OSCE Guide was created by practising doctors who spent years on both
            sides of the assessment room. We designed the platform for real exam
            days, when timetables shift, rooms change, and faculty need tools
            that keep the circuit moving.
          </p>
          <p className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
            We built what we wished we had when running circuits ourselves: clear
            oversight for supervisors, consistent virtual patients for every
            candidate, and feedback that maps to your marking criteria.
          </p>
        </div>
        <div className="mt-7 flex items-center gap-2.5 border-t border-landing-warm pt-[22px]">
          <span className="font-landing-heading text-base font-semibold text-osce-ink-900">
            OSCE Guide
          </span>
          <span className="font-landing-body text-[15px] text-b2c-text-secondary">
            Built by clinicians, for exam day
          </span>
        </div>
      </div>
    </section>
  );
}
