import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { DEMO_MAILTO } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsCtaSection() {
  const type = institutionsLandingType;

  return (
    <section
      id="contact"
      className={`scroll-mt-20 ${landingSectionSurfaces.founders} ${type.sectionPadding}`}
    >
      <div className={`${type.sectionShell} mx-auto max-w-[720px] text-center`}>
        <h2 className={type.sectionTitle}>See OSCE Guide for your programme</h2>
        <p className={type.sectionSubtitleCentered}>
          Book a demo to walk through training sessions, exam circuits, and how
          we support your faculty on the day.
        </p>
        <div className="mt-8 flex justify-center">
          <a href={DEMO_MAILTO} className={type.ctaInk}>
            Book a demo
          </a>
        </div>
      </div>
    </section>
  );
}
