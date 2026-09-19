"use client";

import type { ReactNode } from "react";
import { HiOutlineChevronDown } from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";
import {
  platformStaffFilterBox,
  platformStaffFilterDivider,
  platformStaffFilterSection,
} from "@/domains/platform/platformStaffChrome";

const ghostSelectClass =
  "w-full min-w-0 appearance-none rounded-md border-0 bg-transparent py-1.5 pl-2 pr-7 text-osce-meta font-medium text-osce-ink-900 hover:bg-b2c-surface-muted focus:outline-none focus:ring-2 focus:ring-osce-accent/20";

const ghostSearchClass =
  "w-full min-w-0 border-0 bg-transparent py-1.5 pl-2 pr-2 text-osce-meta font-medium text-osce-ink-900 placeholder:text-b2c-text-muted focus:outline-none focus:ring-0";

/** Right-aligned filter row — matches BMJ partner dashboard `DashboardFilterBar`. */
export function PlatformFilterBar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn(platformStaffFilterSection, className)}>
      <div className="flex justify-end">
        <div className={platformStaffFilterBox}>{children}</div>
      </div>
    </section>
  );
}

export function PlatformFilterDivider() {
  return <div className={platformStaffFilterDivider} aria-hidden />;
}

export function PlatformFilterSelect({
  value,
  onChange,
  children,
  "aria-label": ariaLabel,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  "aria-label": string;
  className?: string;
}) {
  return (
    <label className={cn("relative flex min-w-0 flex-1 basis-0 items-center px-1 py-0.5", className)}>
      <select
        aria-label={ariaLabel}
        className={ghostSelectClass}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
      <HiOutlineChevronDown
        className="pointer-events-none absolute right-2 h-3.5 w-3.5 text-b2c-text-muted"
        aria-hidden
      />
    </label>
  );
}

export function PlatformFilterSearch({
  value,
  onChange,
  placeholder,
  "aria-label": ariaLabel,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  "aria-label"?: string;
  className?: string;
}) {
  const label = ariaLabel ?? placeholder;
  return (
    <label
      className={cn(
        "relative flex min-w-0 flex-[1.35] basis-0 items-center px-1 py-0.5 sm:min-w-[10rem]",
        className,
      )}
    >
      <span className="sr-only">{label}</span>
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={label}
        className={ghostSearchClass}
      />
    </label>
  );
}
