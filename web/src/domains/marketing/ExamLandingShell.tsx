"use client";

import type { ReactNode } from "react";
import { ExamLandingNav } from "./ExamLandingNav";
import { PartnerWelcomeBanner } from "./PartnerWelcomeBanner";
import type { ExamKey } from "./landingExams";
import {
  LandingVariantProvider,
  useLandingVariant,
} from "./LandingVariantContext";

type ExamLandingShellProps = {
  appType: ExamKey;
  registerLabel?: string;
  children: ReactNode;
};

function ExamLandingShellInner({
  appType,
  registerLabel,
  children,
}: ExamLandingShellProps) {
  const { theme } = useLandingVariant();

  return (
    <div {...theme.rootProps}>
      <ExamLandingNav appType={appType} registerLabel={registerLabel} />
      <PartnerWelcomeBanner className="mx-auto mt-3 w-[min(100%-2rem,72rem)]" />
      {children}
    </div>
  );
}

export function ExamLandingShell({
  appType,
  registerLabel,
  children,
}: ExamLandingShellProps) {
  return (
    <LandingVariantProvider variant="exam">
      <ExamLandingShellInner appType={appType} registerLabel={registerLabel}>
        {children}
      </ExamLandingShellInner>
    </LandingVariantProvider>
  );
}
