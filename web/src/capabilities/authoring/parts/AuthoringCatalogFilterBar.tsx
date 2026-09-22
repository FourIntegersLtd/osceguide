"use client";

import type { ReactNode } from "react";
import {
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
} from "@/foundation/ui";
import { AUTHORING_ALL_EXAMS } from "@/capabilities/authoring/parts/examCatalogFilter";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";

export function AuthoringCatalogFilterBar({
  examCode,
  onExamCodeChange,
  search,
  onSearchChange,
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
