"use client";

import { LuHeartHandshake } from "react-icons/lu";
import { HiOutlineClock } from "react-icons/hi2";
import { LandingIconBadge } from "./LandingIconBadge";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import type { LandingIconColor } from "./landingIconPalette";
import { useLandingVariant } from "./LandingVariantContext";

const SUPPORT_ITEMS: Array<{
  icon: typeof LuHeartHandshake;
  color: LandingIconColor;
  title: string;
  description: string;
}> = [
  {
    icon: LuHeartHandshake,
    color: "violet",
    title: "Extra time when you need it",
    description:
      "Turn on Extra Time in your Profile if you need additional time to support your neurodiverse learning needs. Your practice will use your chosen durations for every station.",
  },
  {
    icon: HiOutlineClock,
    color: "teal",
    title: "Your reading and simulation timers",
    description:
      "Configure your own reading and simulation timers so practice matches your exam arrangements or how you learn best.",
  },
];

export function NeurodiversitySupportSection() {
  const { type } = useLandingVariant();

  return (
    <section
      id="neurodiversity"
      className={`scroll-mt-20 ${landingSectionSurfaces.neuro} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <div className="max-w-[56ch]">
          <h2 className={type.sectionTitle}>
            We support our neurodiverse colleagues
          </h2>
          <p className={type.sectionSubtitle}>
            OSCE Guide is built to be inclusive. If you need extra time for your
            learning, we have you covered. No questions asked.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-5 md:grid-cols-2">
          {SUPPORT_ITEMS.map((item) => (
            <div key={item.title} className={type.featureCard}>
              <div className="mb-4">
                <LandingIconBadge icon={item.icon} color={item.color} size="sm" />
              </div>
              <h3 className={type.itemTitle}>{item.title}</h3>
              <p className={`mt-2 ${type.itemBody}`}>{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
