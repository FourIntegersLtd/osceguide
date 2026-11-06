"use client";

import { filtersActive, NO_SITTING_FILTERS, type SittingFilters } from "@/domains/assess/support";
import { boardPad, boardInput, boardLabel } from "@/foundation/ui/boardKit";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/** Kind, exam, dates and name search, applied by the server so they cover every page (status is the tab strip). */
export function SittingFilterBar({
  filters,
  onChange,
  programmes,
  search,
  onSearch,
}: {
  filters: SittingFilters;
  onChange: (next: SittingFilters) => void;
  programmes: { id: string; exam_name: string }[];
  search: string;
  onSearch: (value: string) => void;
}) {
  const w = useAssessWords();
  const set = (patch: Partial<SittingFilters>) => onChange({ ...filters, ...patch });
  return (
    <div className={boardPad} style={{ gap: 12 }}>
      <div className="flex flex-wrap gap-4" role="group" aria-label={`Filter ${w.sittings}`}>
        <div className="min-w-0 flex-[1_1_200px]">
          <label className={boardLabel} htmlFor="sitting-kind">Kind</label>
          <select id="sitting-kind" className={boardInput} value={filters.mode} onChange={(e) => set({ mode: e.target.value })}>
            <option value="">All kinds</option>
            <option value="exam">Formal exam</option>
            <option value="training">Training</option>
          </select>
        </div>
        <div className="min-w-0 flex-[1_1_200px]">
          <label className={boardLabel} htmlFor="sitting-exam">Exam</label>
          <select id="sitting-exam" className={boardInput} value={filters.programmeId} onChange={(e) => set({ programmeId: e.target.value })}>
            <option value="">Any exam</option>
            {programmes.map((programme) => (
              <option key={programme.id} value={programme.id}>
                {programme.exam_name}
              </option>
            ))}
          </select>
        </div>
        <div className="min-w-0 flex-[1_1_200px]">
          <label className={boardLabel} htmlFor="sitting-from">From</label>
          <input id="sitting-from" className={boardInput} type="date" value={filters.from} onChange={(e) => set({ from: e.target.value })} />
        </div>
        <div className="min-w-0 flex-[1_1_200px]">
          <label className={boardLabel} htmlFor="sitting-to">To</label>
          <input id="sitting-to" className={boardInput} type="date" value={filters.to} onChange={(e) => set({ to: e.target.value })} />
        </div>
        <div className="min-w-0 flex-[2_1_260px]">
          <label className={boardLabel} htmlFor="sitting-search">Search</label>
          <input
            id="sitting-search"
            className={boardInput}
            placeholder={`Search by ${w.sitting} name`}
            value={search}
            onChange={(e) => onSearch(e.target.value)}
          />
        </div>
      </div>
      <div className="min-h-[21px] text-assess-label">
        <button
          type="button"
          className="text-assess-label text-osce-accent hover:text-osce-accent-hover"
          onClick={() => onChange(NO_SITTING_FILTERS)}
          disabled={!filtersActive(filters) && search === ""}
        >
          Clear filters
        </button>
      </div>
    </div>
  );
}
