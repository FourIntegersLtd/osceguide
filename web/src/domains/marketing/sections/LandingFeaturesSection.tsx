"use client";

import { landingSectionSurfaces } from "../landingSectionSurfaces";
import { useLandingVariant } from "../LandingVariantContext";
import { CLASSIC_LANDING_FEATURES } from "./landingFeatureContent";
import { LandingFeatureCards } from "./LandingFeatureCards";
import { LandingProductRail } from "./LandingProductRail";

export function LandingFeaturesSection() {
  const { type } = useLandingVariant();

  return (
    <section
      id="features"
      className={`scroll-mt-20 ${landingSectionSurfaces.features} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <h2 className={type.sectionTitle}>Your Complete OSCE Solution</h2>
        <p className={`${type.sectionSubtitle} max-w-[52ch]`}>
          Built by clinicians, focusing on what matters most for your success
        </p>

        <LandingFeatureCards features={CLASSIC_LANDING_FEATURES} />

        <LandingProductRail />
      </div>
    </section>
  );
}
