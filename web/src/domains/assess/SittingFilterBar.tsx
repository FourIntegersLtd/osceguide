"use client";

import { useState } from "react";
import { Button, Input, Select } from "@/foundation/ui";
import { filtersActive, NO_SITTING_FILTERS, type SittingFilters } from "@/domains/assess/support";

const STATUSES: [string, string][] = [
  ["scheduled", "Scheduled"],
  ["in_progress", "Running"],
  ["completed", "Finished"],
  ["cancelled", "Cancelled"],
];

/** Kind, status, exam and date behind one Filters button, applied by the server so they cover every page. */
export function SittingFilterBar({
  filters,
  onChange,
  programmes,
}: {
  filters: SittingFilters;
  onChange: (next: SittingFilters) => void;
  programmes: { id: string; exam_name: string }[];
}) {
  const set = (patch: Partial<SittingFilters>) => onChange({ ...filters, ...patch });
  const [open, setOpen] = useState(filtersActive({ ...filters, search: "" }));
  return (
    <div className="flex flex-col gap-3">
      <div>
        <Button
          themeType="b2b"
          variant="secondary"
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
        >
          Filters
        </Button>
      </div>
      {open ? (
    <div className="flex flex-wrap items-end gap-3" role="group" aria-label="Filter sittings">
      <Select
        label="Kind"
        className="w-auto"
        value={filters.mode}
        onChange={(e) => set({ mode: e.target.value })}
      >
        <option value="">All kinds</option>
        <option value="exam">Formal exam</option>
        <option value="training">Training</option>
      </Select>
      <Select
        label="Status"
        className="w-auto"
        value={filters.status}
        onChange={(e) => set({ status: e.target.value })}
      >
        <option value="">Any status</option>
        {STATUSES.map(([status, label]) => (
          <option key={status} value={status}>
            {label}
          </option>
        ))}
      </Select>
      <Select
        label="Exam"
        className="w-auto"
        value={filters.programmeId}
        onChange={(e) => set({ programmeId: e.target.value })}
      >
        <option value="">Any exam</option>
        {programmes.map((programme) => (
          <option key={programme.id} value={programme.id}>
            {programme.exam_name}
          </option>
        ))}
      </Select>
      <Input label="From" type="date" value={filters.from} onChange={(e) => set({ from: e.target.value })} />
      <Input label="To" type="date" value={filters.to} onChange={(e) => set({ to: e.target.value })} />
      {filtersActive(filters) ? (
        <button type="button" className="text-osce-meta underline" onClick={() => onChange(NO_SITTING_FILTERS)}>
          Clear filters
        </button>
      ) : null}
    </div>
      ) : null}
    </div>
  );
}
