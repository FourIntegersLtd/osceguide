"use client";

import { Input, Select } from "@/foundation/ui";
import { humanise } from "@/foundation/format";
import { filtersActive, NO_SITTING_FILTERS, type SittingFilters } from "@/domains/assess/support";

const STATUSES = ["scheduled", "in_progress", "completed", "cancelled"];

/** Status, programme and date, applied by the server so they cover every page. */
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
  return (
    <div className="flex flex-wrap items-end gap-3" role="group" aria-label="Filter sittings">
      <Select
        label="Status"
        className="w-auto"
        value={filters.status}
        onChange={(e) => set({ status: e.target.value })}
      >
        <option value="">Any status</option>
        {STATUSES.map((status) => (
          <option key={status} value={status}>
            {humanise(status)}
          </option>
        ))}
      </Select>
      <Select
        label="Programme"
        className="w-auto"
        value={filters.programmeId}
        onChange={(e) => set({ programmeId: e.target.value })}
      >
        <option value="">Any programme</option>
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
  );
}
