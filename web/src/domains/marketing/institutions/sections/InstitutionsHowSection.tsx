import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { InstitutionsHowSteps } from "../components/InstitutionsHowSteps";
import { MarketingPill } from "../components/MarketingPill";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsHowSection() {
  const type = institutionsLandingType;

  return (
    <section
      id="how"
      className={`scroll-mt-20 ${landingSectionSurfaces.plain} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <MarketingPill>How it works</MarketingPill>
        <h2 className={`${type.sectionTitle} mt-5 max-w-[30ch]`}>
          From candidate consultation to faculty oversight
        </h2>
        <p className={`${type.sectionSubtitle} max-w-[62ch]`}>
          Each station follows a fixed sequence: the candidate consults a virtual
          patient by voice, supervisors observe in real time, and feedback is
          recorded against your marking criteria.
        </p>
        <InstitutionsHowSteps />
      </div>
    </section>
  );
}
