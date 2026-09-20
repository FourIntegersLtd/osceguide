"use client";

import type { ReactNode } from "react";
import { B2CPageHeader } from "@/foundation/ui";
import { platformStaffPanel } from "@/domains/platform/platformStaffChrome";

/** Staff template wizards — light gray panel (B2C borders). */
export function PlatformTemplateWizardPageLayout({
  eyebrow,
  title,
  subtitle,
  backHref,
  backLabel = "Templates",
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  backHref: string;
  backLabel?: string;
  children: ReactNode;
}) {
  const description = subtitle ? `${eyebrow} — ${subtitle}` : eyebrow;

  return (
    <div className="flex w-full flex-col gap-4 pb-8">
      <B2CPageHeader
        title={title}
        subtitle={description}
        back={{ href: backHref, label: backLabel }}
        className="mb-0"
      />
      <div className={platformStaffPanel}>{children}</div>
    </div>
  );
}
