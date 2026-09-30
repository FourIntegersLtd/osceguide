"use client";

import { landingSections } from "./landingConfig";
import { LandingNav } from "./LandingNav";
import { LandingSection } from "./sections/landingSectionRegistry";
import {
  LandingVariantProvider,
  useLandingVariant,
} from "./LandingVariantContext";

function LandingPageContent() {
  const { theme } = useLandingVariant();

  return (
    <div {...theme.rootProps}>
      <LandingNav />
      {landingSections.map((sectionKey) => (
        <LandingSection key={sectionKey} sectionKey={sectionKey} />
      ))}
    </div>
  );
}

export function LandingPage() {
  return (
    <LandingVariantProvider>
      <LandingPageContent />
    </LandingVariantProvider>
  );
}

export default LandingPage;
