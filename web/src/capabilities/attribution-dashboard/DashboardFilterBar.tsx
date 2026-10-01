"use client";

import { useState, type ReactNode } from "react";
import { HiOutlineChevronDown } from "react-icons/hi2";
import { CustomDateRangeModal } from "@/capabilities/attribution-dashboard/CustomDateRangeModal";
import {
  RANGE_PRESET_LABELS,
  RANGE_PRESET_ORDER,
  detectRangePreset,
  formatActiveFilterSummary,
  formatDateRangeLabel,
  hasActiveFilters,
  type ConcreteRangePreset,
} from "@/capabilities/attribution-dashboard/presets";
import type { FilterScope } from "@/capabilities/attribution-dashboard/tabs";
import {
  PILOT_EXAMS,
  PILOT_PARTNERS,
  type AttributionFilters,
  type AttributionMode,
} from "@/capabilities/attribution-dashboard/types";

interface DashboardFilterBarProps {
  filters: AttributionFilters;
  onChange: (next: Partial<AttributionFilters>) => void;
  scope: FilterScope;
  mode: AttributionMode;
  onPresetSelect: (preset: ConcreteRangePreset) => void;
  onReset: () => void;
}

const ghostSelectClass =
  "w-full min-w-0 appearance-none rounded-osce-md border-0 bg-transparent py-1.5 pl-2 pr-7 text-osce-meta font-medium text-ink hover:bg-canvas focus:outline-none focus:ring-2 focus:ring-accent/30";

function FilterSelect({
  value,
  onChange,
  children,
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  "aria-label": string;
}) {
  return (
    <label className="relative flex min-w-0 flex-1 basis-0 items-center px-1 py-0.5">
      <select
        aria-label={ariaLabel}
        className={ghostSelectClass}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
      <HiOutlineChevronDown
        className="pointer-events-none absolute right-2 h-3.5 w-3.5 text-ink-subtle"
        aria-hidden
      />
    </label>
  );
}

function Divider() {
  return <div className="w-px shrink-0 self-stretch bg-border" aria-hidden />;
}

function PartnerSelect({
  filters,
  onChange,
}: {
  filters: AttributionFilters;
  onChange: (next: Partial<AttributionFilters>) => void;
}) {
  return (
    <FilterSelect
      aria-label="Partner"
      value={filters.partner}
      onChange={(partner) => onChange({ partner })}
    >
      {PILOT_PARTNERS.map((partner) => (
        <option key={partner} value={partner}>
          {partner.toUpperCase()}
        </option>
      ))}
    </FilterSelect>
  );
}

/**
 * Date range, partner (staff only) and exam, as one bordered group.
 *
 * Every change goes to the URL, and from there to the server: the bar holds no
 * rows and filters none. "Custom" opens a modal rather than a second pair of
 * inputs, so the group stays one line wide.
 */
export function DashboardFilterBar({
  filters,
  onChange,
  scope,
  mode,
  onPresetSelect,
  onReset,
}: DashboardFilterBarProps) {
  const [customOpen, setCustomOpen] = useState(false);
  if (scope === "hidden") return null;

  const summary = formatActiveFilterSummary(filters, mode);

  if (scope === "partner-only") {
    return (
      <section className="space-y-2 border-b border-border pb-4">
        <div className="flex justify-end">
          <div className="inline-flex min-w-0 max-w-full items-stretch rounded-osce-md border border-border bg-surface">
            <PartnerSelect filters={filters} onChange={onChange} />
          </div>
        </div>
        <p className="text-right text-osce-caption text-ink-subtle">{summary}</p>
      </section>
    );
  }

  const activePreset = detectRangePreset(filters.fromDate, filters.toDate);

  return (
    <>
      <section className="space-y-2 border-b border-border pb-4">
        <div className="flex justify-end">
          <div className="inline-flex w-full max-w-md min-w-0 items-stretch rounded-osce-md border border-border bg-surface sm:w-auto sm:min-w-[18rem]">
            <FilterSelect
              aria-label="Date range"
              value={activePreset}
              onChange={(value) => {
                if (value === "custom") setCustomOpen(true);
                else onPresetSelect(value as ConcreteRangePreset);
              }}
            >
              {RANGE_PRESET_ORDER.map((preset) => (
                <option key={preset} value={preset}>
                  {RANGE_PRESET_LABELS[preset]}
                </option>
              ))}
              <option value="custom">
                {activePreset === "custom"
                  ? formatDateRangeLabel(filters.fromDate, filters.toDate)
                  : "Custom"}
              </option>
            </FilterSelect>
            {mode === "internal" ? (
              <>
                <Divider />
                <PartnerSelect filters={filters} onChange={onChange} />
              </>
            ) : null}
            <Divider />
            <FilterSelect
              aria-label="Exam"
              value={filters.exam}
              onChange={(exam) => onChange({ exam })}
            >
              <option value="">All exams</option>
              {PILOT_EXAMS.map((exam) => (
                <option key={exam} value={exam}>
                  {exam.toUpperCase()}
                </option>
              ))}
            </FilterSelect>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-osce-caption text-ink-subtle">
          <span>{summary} · UK calendar days</span>
          {hasActiveFilters(filters) ? (
            <button
              type="button"
              onClick={onReset}
              className="font-medium text-accent hover:underline"
            >
              Reset filters
            </button>
          ) : null}
        </div>
      </section>
      <CustomDateRangeModal
        open={customOpen}
        fromDate={filters.fromDate}
        toDate={filters.toDate}
        onClose={() => setCustomOpen(false)}
        onApply={(range) => onChange(range)}
      />
    </>
  );
}
