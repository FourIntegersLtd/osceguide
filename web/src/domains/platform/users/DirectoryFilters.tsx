"use client";

import {
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
} from "@/foundation/ui";
import type { DirectoryFilters as Filters, ExamDirectorySummary } from "@/domains/platform/api";
import { ACCESS_FILTERS, USER_STATUSES, planLabel } from "@/domains/platform/users/vocabulary";

/**
 * The directory's filter row. Every control is one of the backend's facets,
 * so changing one reloads rather than narrowing what happened to be paged in.
 * The search box submits on Enter, as the old console's did.
 */
export function DirectoryFilters({
  exams,
  plans,
  filters,
  term,
  onTerm,
  onChange,
}: {
  exams: ExamDirectorySummary[];
  plans: string[];
  filters: Filters;
  term: string;
  onTerm: (value: string) => void;
  onChange: (next: Filters) => void;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onChange({ ...filters, q: term.trim() || null });
      }}
    >
      <PlatformFilterBar>
        <PlatformFilterSelect
          aria-label="Exam"
          value={filters.examCode ?? ""}
          onChange={(value) => onChange({ ...filters, examCode: value || null })}
        >
          <option value="">All exams</option>
          {exams.map((exam) => (
            <option key={exam.code} value={exam.code}>
              {exam.name || exam.code.toUpperCase()}
            </option>
          ))}
        </PlatformFilterSelect>
        <PlatformFilterDivider />
        <PlatformFilterSelect
          aria-label="Access"
          value={filters.access ?? ""}
          onChange={(value) => onChange({ ...filters, access: value || null })}
        >
          <option value="">Any access</option>
          {ACCESS_FILTERS.map((entry) => (
            <option key={entry.value} value={entry.value}>
              {entry.label}
            </option>
          ))}
        </PlatformFilterSelect>
        <PlatformFilterDivider />
        <PlatformFilterSelect
          aria-label="Plan"
          value={filters.planCode ?? ""}
          onChange={(value) => onChange({ ...filters, planCode: value || null })}
        >
          <option value="">Any plan</option>
          {plans.map((code) => (
            <option key={code} value={code}>
              {planLabel(code)}
            </option>
          ))}
        </PlatformFilterSelect>
        <PlatformFilterDivider />
        <PlatformFilterSelect
          aria-label="Status"
          value={filters.status ?? ""}
          onChange={(value) => onChange({ ...filters, status: value || null })}
        >
          <option value="">Any status</option>
          {USER_STATUSES.map((entry) => (
            <option key={entry.value} value={entry.value}>
              {entry.label}
            </option>
          ))}
        </PlatformFilterSelect>
        <PlatformFilterDivider />
        <PlatformFilterSearch
          value={term}
          onChange={onTerm}
          placeholder="Search email or name"
          aria-label="Search accounts by email or name"
        />
      </PlatformFilterBar>
    </form>
  );
}
