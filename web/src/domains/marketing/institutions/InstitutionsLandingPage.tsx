import { SiteShell } from "@/domains/marketing/site/SiteShell";
import { INSTITUTIONS_NAV } from "./institutionsLandingContent";
import {
  InstitutionsAboutSection,
  InstitutionsBuyerSection,
  InstitutionsCtaSection,
  InstitutionsHeroSection,
  InstitutionsHowSection,
  InstitutionsModesSection,
  InstitutionsPlatformSection,
  InstitutionsValueSection,
} from "./sections/InstitutionsSections";

export function InstitutionsLandingPage() {
  return (
    <SiteShell links={INSTITUTIONS_NAV}>
      <InstitutionsHeroSection />
      <InstitutionsValueSection />
      <InstitutionsBuyerSection />
      <InstitutionsHowSection />
      <InstitutionsPlatformSection />
      <InstitutionsModesSection />
      <InstitutionsAboutSection />
      <InstitutionsCtaSection />
    </SiteShell>
  );
}
