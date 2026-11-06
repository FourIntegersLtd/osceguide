"use client";

import type { ReactNode } from "react";
import {
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
  Select,
} from "@/foundation/ui";
import { STATION_STATUS_FILTERS, type StationStatusFilter } from "@/capabilities/authoring/parts/stationListUrl";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";
import { boardInput } from "@/foundation/ui/boardKit";

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
  const { options, loading, error } = useAuthoringExamCatalog();
  const chrome = useAuthoringChrome();

  if (!chrome.b2c) {
    return (
      <div className={`flex flex-wrap gap-2 ${className ?? ""}`}>
        {leading}
        <Select
          aria-label="Filter by exam"
          value={examCode}
          onChange={(e) => onExamCodeChange(e.target.value)}
          className="max-w-[200px]"
        >
          <option value={AUTHORING_ALL_EXAMS}>{loading ? "Loading exams…" : error ? "Exams unavailable" : "All exams"}</option>
          {options.map((exam) => (
            <option key={exam.code} value={exam.code}>
              {exam.label}
            </option>
          ))}
        </Select>
        {status && onStatusChange ? (
          <Select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => onStatusChange(e.target.value as StationStatusFilter)}
            className="max-w-[160px]"
          >
            {STATION_STATUS_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        ) : null}
        {onSearchChange ? (
          <input
            value={search ?? ""}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            aria-label={searchAriaLabel}
            className={`${boardInput} flex-[1_1_240px]`}
          />
        ) : null}
        {trailing}
      </div>
    );
  }

  return (
    <PlatformFilterBar leading={leading} trailing={trailing} className={className}>
      <PlatformFilterSelect
        aria-label="Filter by exam"
        value={examCode}
        onChange={onExamCodeChange}
        className="min-w-[9rem] sm:min-w-[11rem]"
      >
        <option value={AUTHORING_ALL_EXAMS}>{loading ? "Loading exams…" : error ? "Exams unavailable" : "All exams"}</option>
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
