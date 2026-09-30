"use client";

import { createContext, useContext, type ReactNode } from "react";
import { createLandingType, type LandingType } from "./landingTypography";
import {
  getLandingTheme,
  type LandingAccent,
  type LandingTheme,
  type LandingThemeVariant,
} from "@/foundation/ui/landingTheme";

type LandingVariantContextValue = {
  type: LandingType;
  theme: LandingTheme;
  accent: LandingAccent;
};

const examFallback: LandingVariantContextValue = {
  type: createLandingType("exam"),
  theme: getLandingTheme("exam"),
  accent: getLandingTheme("exam").accent,
};

const classicValue: LandingVariantContextValue = {
  type: createLandingType("classic"),
  theme: getLandingTheme("classic"),
  accent: getLandingTheme("classic").accent,
};

const LandingVariantContext =
  createContext<LandingVariantContextValue | null>(null);

type LandingVariantProviderProps = {
  children: ReactNode;
  variant?: LandingThemeVariant;
};

export function LandingVariantProvider({
  children,
  variant = "classic",
}: LandingVariantProviderProps) {
  const value = variant === "exam" ? examFallback : classicValue;

  return (
    <LandingVariantContext.Provider value={value}>
      {children}
    </LandingVariantContext.Provider>
  );
}

export function useLandingVariant(): LandingVariantContextValue {
  const context = useContext(LandingVariantContext);
  return context ?? examFallback;
}

export type { LandingThemeVariant };
