"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import {
  HiOutlineClipboardDocumentCheck,
  HiOutlineMicrophone,
  HiOutlineUserGroup,
} from "react-icons/hi2";
import { LandingIconBadge } from "../LandingIconBadge";
import type { LandingIconColor } from "../landingIconPalette";
import type { LandingFeatureItem } from "./landingFeatureContent";
import { useLandingVariant } from "../LandingVariantContext";

const ICONS: Record<
  LandingFeatureItem["icon"],
  ComponentType<{ className?: string }>
> = {
  simulation: HiOutlineMicrophone,
  colleagues: HiOutlineUserGroup,
  feedback: HiOutlineClipboardDocumentCheck,
};

const ICON_COLOR: Record<LandingFeatureItem["icon"], LandingIconColor> = {
  simulation: "cyan",
  colleagues: "green",
  feedback: "indigo",
};

type LandingFeatureCardsProps = {
  features: LandingFeatureItem[];
};

export function LandingFeatureCards({ features }: LandingFeatureCardsProps) {
  const { type } = useLandingVariant();

  return (
    <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-3 lg:gap-10">
      {features.map((feature) => (
        <article key={feature.title} className="flex gap-3.5">
          <LandingIconBadge
            icon={ICONS[feature.icon]}
            color={ICON_COLOR[feature.icon]}
          />
          <div className="min-w-0 pt-0.5">
            <h3 className={type.itemTitle}>{feature.title}</h3>
            <p className={`mt-1.5 ${type.itemBody}`}>{feature.description}</p>
            <Link href={feature.href} className={`mt-3 inline-block ${type.linkAction}`}>
              Learn more →
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
