"use client";

import type { ReactNode } from "react";
import { PlatformPageHeader, platformStaffPanel } from "@/foundation/ui";

/** Staff authoring wizards: the console header with a back link, then one panel holding the form. */
export function PlatformTemplateWizardPageLayout({
  title,
  subtitle,
  backHref,
  backLabel = "Templates",
  children,
}: {
  title: string;
  subtitle?: string;
  backHref: string;
  backLabel?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex w-full flex-col gap-6 pb-8">
      <PlatformPageHeader
        title={title}
        description={subtitle}
        back={{ href: backHref, label: backLabel }}
      />
      <div className={platformStaffPanel}>{children}</div>
    </div>
  );
}
