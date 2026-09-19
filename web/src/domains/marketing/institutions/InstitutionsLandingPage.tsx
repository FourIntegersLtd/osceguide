"use client";

import { B2BLandingFooter } from "@/domains/marketing/institutions/B2BLandingFooter";
import { InstitutionsBuyerSection } from "./sections/InstitutionsBuyerSection";
import { InstitutionsCtaSection } from "./sections/InstitutionsCtaSection";
import { InstitutionsHeroSection } from "./sections/InstitutionsHeroSection";
import { InstitutionsHowSection } from "./sections/InstitutionsHowSection";
import { InstitutionsLandingNav } from "./sections/InstitutionsLandingNav";
import { InstitutionsModesSection } from "./sections/InstitutionsModesSection";
import { InstitutionsPlatformSection } from "./sections/InstitutionsPlatformSection";
import { InstitutionsAboutSection } from "./sections/InstitutionsAboutSection";
import { InstitutionsValueSection } from "./sections/InstitutionsValueSection";
import { institutionsLandingTheme } from "./institutionsLandingType";

export function InstitutionsLandingPage() {
  const { rootProps } = institutionsLandingTheme;

  return (
    <div
      {...rootProps}
      className={`${rootProps.className} font-landing-body`}
    >
      <InstitutionsLandingNav />
      <InstitutionsHeroSection />
      <InstitutionsValueSection />
      <InstitutionsBuyerSection />
      <InstitutionsHowSection />
      <InstitutionsPlatformSection />
      <InstitutionsModesSection />
      <InstitutionsAboutSection />
      <InstitutionsCtaSection />
      <B2BLandingFooter variant="marketing" />
    </div>
  );
}
