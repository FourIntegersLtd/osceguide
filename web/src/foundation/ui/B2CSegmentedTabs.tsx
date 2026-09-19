"use client";

import type { ReactNode } from "react";
import {
  b2cSegmentedControl,
  b2cSegmentedTabActive,
  b2cSegmentedTabInactive,
  b2cSegmentedTabLabelActive,
  b2cSegmentedTabLabelInactive,
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
  "aria-label"?: string;
};

export function B2CSegmentedTabs<T extends string = string>({
  items,
  value,
  onChange,
  className = "",
  "aria-label": ariaLabel = "Tabs",
}: B2CSegmentedTabsProps<T>) {
  return (
    <div className={className}>
      <div className={b2cSegmentedControl} role="tablist" aria-label={ariaLabel}>
        {items.map((item) => {
          const isActive = value === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              disabled={item.disabled}
              className={
                isActive ? b2cSegmentedTabActive : b2cSegmentedTabInactive
              }
              onClick={() => {
                if (!item.disabled) onChange(item.id);
              }}
            >
              <span
                className={
                  isActive
                    ? b2cSegmentedTabLabelActive
                    : b2cSegmentedTabLabelInactive
                }
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
