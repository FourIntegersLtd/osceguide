import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { InstitutionsValueFeatureCards } from "../components/InstitutionsValueFeatureCards";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsValueSection() {
  const type = institutionsLandingType;

  return (
    <section className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPadding}`}>
      <div className={type.sectionShell}>
        <p className={type.eyebrow}>What OSCE Guide does</p>
        <h2 className={`${type.sectionTitle} mt-5 max-w-[26ch]`}>
          Your complete OSCE platform for institutions
        </h2>
        <p className={`${type.sectionSubtitle} max-w-[60ch]`}>
          Practice, feedback, and exam-day workflows in one platform.
        </p>
        <InstitutionsValueFeatureCards />
      </div>
    </section>
  );
}
