"use client";

import type { ReactNode } from "react";
import {
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
} from "@/foundation/ui";
import { STATION_STATUS_FILTERS, type StationStatusFilter } from "@/capabilities/authoring/parts/stationListUrl";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";

export function AuthoringCatalogFilterBar({
  examCode,
  onExamCodeChange,
  search,
  onSearchChange,
  status,
  onStatusChange,
  searchPlaceholder = "Search…",
  searchAriaLabel = "Search catalogue",
  leading,
  trailing,
  className,
}: {
  examCode: string;
  onExamCodeChange: (code: string) => void;
  search?: string;
  onSearchChange?: (value: string) => void;
  /** The stations list's Active / Archived / All; other catalogues leave it out. */
  status?: StationStatusFilter;
  onStatusChange?: (value: StationStatusFilter) => void;
  searchPlaceholder?: string;
  searchAriaLabel?: string;
  leading?: ReactNode;
  trailing?: ReactNode;
  className?: string;
}) {
  const { options, loading } = useAuthoringExamCatalog();

  return (
    <PlatformFilterBar leading={leading} trailing={trailing} className={className}>
      <PlatformFilterSelect
        aria-label="Filter by exam"
        value={examCode}
        onChange={onExamCodeChange}
        className="min-w-[9rem] sm:min-w-[11rem]"
      >
        <option value={AUTHORING_ALL_EXAMS}>{loading ? "Loading exams…" : "All exams"}</option>
        {options.map((exam) => (
          <option key={exam.code} value={exam.code}>
            {exam.label}
          </option>
        ))}
      </PlatformFilterSelect>
      {status && onStatusChange ? (
        <>
          <PlatformFilterDivider />
          <PlatformFilterSelect
            aria-label="Filter by status"
            value={status}
            onChange={(value) => onStatusChange(value as StationStatusFilter)}
            className="min-w-[7rem]"
          >
            {STATION_STATUS_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </PlatformFilterSelect>
        </>
      ) : null}
      {onSearchChange ? (
        <>
          <PlatformFilterDivider />
          <PlatformFilterSearch
            value={search ?? ""}
            onChange={onSearchChange}
            placeholder={searchPlaceholder}
            aria-label={searchAriaLabel}
          />
        </>
      ) : null}
    </PlatformFilterBar>
  );
}
