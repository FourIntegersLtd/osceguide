"use client";

import { LuTimer } from "react-icons/lu";
import { HiOutlineBolt, HiOutlineCalendarDays } from "react-icons/hi2";
import { LandingIconBadge } from "./LandingIconBadge";
import { landingSectionSurfaces } from "./landingSectionSurfaces";
import type { LandingIconColor } from "./landingIconPalette";
import { PracticeColleaguesShowcase } from "./PracticeColleaguesShowcase";
import { useLandingVariant } from "./LandingVariantContext";

const DEFAULT_SUBTITLE =
  "Choose between instant matching or scheduled sessions and practice in real-time video consultations.";

const DEFAULT_ITEMS: Array<{
  icon: React.ComponentType<{ className?: string }>;
  color: LandingIconColor;
  title: string;
  description: string;
}> = [
  {
    icon: HiOutlineBolt,
    color: "orange",
    title: "Live Practice",
    description:
      "Get matched instantly with available colleagues and start practicing immediately.",
  },
  {
    icon: HiOutlineCalendarDays,
    color: "green",
    title: "Marketplace",
    description:
      "Post your availability or browse sessions from colleagues. Schedule at times that work for both of you.",
  },
  {
    icon: LuTimer,
    color: "cyan",
    title: "Automatic Timing",
    description:
      "Built-in timer matches the exam format. Practice with realistic time constraints.",
  },
];

type PracticeWithColleaguesSectionProps = {
  subtitle?: string;
  items?: Array<{
    icon: React.ComponentType<{ className?: string }>;
    color: LandingIconColor;
    title: string;
    description: string;
  }>;
};

export function PracticeWithColleaguesSection({
  subtitle = DEFAULT_SUBTITLE,
  items = DEFAULT_ITEMS,
}: PracticeWithColleaguesSectionProps) {
  const { type } = useLandingVariant();

  return (
    <section
      id="practice"
      className={`scroll-mt-20 py-16 sm:py-20 ${landingSectionSurfaces.practice}`}
    >
      <div className={type.sectionShell}>
        <h2 className={type.sectionTitle}>Practice with Colleagues</h2>
        <p className={`${type.sectionSubtitle} max-w-[56ch]`}>{subtitle}</p>

        <div className="mt-10 grid grid-cols-1 items-start gap-10 xl:grid-cols-[minmax(0,340px)_1fr] xl:gap-12">
          <div className="space-y-7">
            {items.map((item) => (
              <div key={item.title} className="flex gap-4">
                <LandingIconBadge icon={item.icon} color={item.color} size="sm" />
                <div>
                  <h3 className={type.itemTitle}>{item.title}</h3>
                  <p className={`mt-1.5 ${type.itemBody}`}>{item.description}</p>
                </div>
              </div>
            ))}
          </div>

          <PracticeColleaguesShowcase />
        </div>
      </div>
    </section>
  );
}
