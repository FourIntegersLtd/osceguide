"use client";

import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import {
  b2cSegmentedControl,
  b2cSegmentedTabActive,
  b2cSegmentedTabInactive,
  b2cSegmentedTabLabelActive,
  b2cSegmentedTabLabelInactive,
  b2cSegmentedTabsSpacing,
} from "@/foundation/ui/productTokens";

export type B2CSegmentedTabItem<T extends string = string> = {
  id: T;
  label: ReactNode;
  disabled?: boolean;
};

export type B2CSegmentedTabsProps<T extends string = string> = {
  items: B2CSegmentedTabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  className?: string;
  /** When true, omit default bottom margin (tabs flush inside a card footer). */
  compact?: boolean;
  "aria-label"?: string;
};

export function B2CSegmentedTabs<T extends string = string>({
  items,
  value,
  onChange,
  className,
  compact = false,
  "aria-label": ariaLabel = "Tabs",
}: B2CSegmentedTabsProps<T>) {
  return (
    <div className={cn(!compact && b2cSegmentedTabsSpacing, className)}>
      <div className={b2cSegmentedControl} role="tablist" aria-label={ariaLabel}>
        {items.map((item) => {
          const isActive = value === item.id;
          const tabClass = isActive ? b2cSegmentedTabActive : b2cSegmentedTabInactive;
          const labelClass = isActive
            ? b2cSegmentedTabLabelActive
            : b2cSegmentedTabLabelInactive;

          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              disabled={item.disabled}
              className={tabClass}
              onClick={() => {
                if (!item.disabled) onChange(item.id);
              }}
            >
              <span className={labelClass}>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
