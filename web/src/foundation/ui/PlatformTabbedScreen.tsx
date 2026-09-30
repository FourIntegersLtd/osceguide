"use client";

import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { B2CSegmentedTabs, type B2CSegmentedTabItem } from "@/foundation/ui/B2CSegmentedTabs";
import { PlatformPageHeader } from "@/foundation/ui/PlatformPageHeader";

/**
 * Staff console screens that use underline tabs — one page title, then tabs, then body.
 * Avoids repeating the screen name in a subtitle and again in section headings.
 */
export function PlatformTabbedScreen<T extends string>({
  title,
  description,
  icon,
  tabs,
  value,
  onChange,
  ariaLabel,
  children,
}: {
  title: string;
  description?: ReactNode;
  icon?: IconType;
  tabs: B2CSegmentedTabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  ariaLabel: string;
  children: ReactNode;
}) {
  return (
    <div className="flex w-full flex-col gap-6">
      <PlatformPageHeader title={title} description={description} icon={icon} />
      <B2CSegmentedTabs
        items={tabs}
        value={value}
        onChange={onChange}
        aria-label={ariaLabel}
        className="mb-0 sm:mb-0"
      />
      {children}
    </div>
  );
}
