"use client";

import { FOUNDERS_LETTER } from "./foundersLetter";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import { useLandingVariant } from "./LandingVariantContext";

export function FoundersMessage() {
  const { type } = useLandingVariant();

  return (
    <section
      className={`scroll-mt-20 py-16 sm:py-20 ${landingSectionSurfaces.founders}`}
    >
      <div className={`${type.sectionShell} max-w-osce-narrow`}>
        <h2 className="font-landing-heading text-[clamp(1.5rem,2.8vw,2rem)] font-semibold leading-[1.2] tracking-[-0.025em] text-osce-ink-900">
          A message from our founders
        </h2>
        <div className="mt-6 flex flex-col gap-[18px]">
          {FOUNDERS_LETTER.map((t) => (
            <p key={t} className="font-landing-body text-[15px] leading-[1.7] text-landing-ink-body sm:text-[17px]">
              {t}
            </p>
          ))}
        </div>
        <p className="mt-7 border-t border-landing-warm pt-[22px] font-landing-body text-[15px]">
          <b className="font-landing-heading text-base font-semibold text-osce-ink-900">Kenny and Aisha</b>, <span className="text-b2c-text-secondary">Co-founders</span>
        </p>
      </div>
    </section>
  );
}

export default FoundersMessage;
