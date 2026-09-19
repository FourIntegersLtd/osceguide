"use client";

import { landingSectionSurfaces } from "../landingSectionSurfaces";
import { useLandingVariant } from "../LandingVariantContext";

export function LandingFeedbackSection() {
  const { type } = useLandingVariant();

  return (
    <section
      id="feedback"
      className={`scroll-mt-20 pb-12 pt-16 sm:pt-20 ${landingSectionSurfaces.feedback}`}
    >
      <div className={type.sectionShell}>
        <div className="mb-10 text-center sm:mb-12">
          <h2 className={type.sectionTitle}>
            Help Us <span className="text-osce-accent">Improve</span>
          </h2>
          <p className={type.sectionSubtitleCentered}>
            Your feedback shapes our platform. Be honest, be bold!
          </p>
        </div>
        {/* The voting widget it used to hold reads and writes a product-feedback
            slice platform-api has not grown yet. This section is not in
            `landingSections` while that is true. */}
        <p className="text-center text-sm text-ink-muted">
          Tell us what would help you most — we read every message.
        </p>
      </div>
    </section>
  );
}
