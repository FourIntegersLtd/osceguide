"use client";

import { LuSearch } from "react-icons/lu";
import { AsyncBoundary, cn } from "@/foundation/ui";
import { b2cInputBase } from "@/foundation/ui/productTokens";
import type { StationLibraryState } from "@/capabilities/stations/useStationLibrary";

/**
 * The two ways into a library of a few hundred scenarios: which exam, and a
 * word from the title.
 *
 * The exam chips come from `/api/v1/exams` rather than a constant, which is
 * the whole reason this screen works for an institution: the retiring client
 * had the four consumer products hard-coded in an array and an organisation's
 * own exam could not appear in it.
 */
export function StationFilters({ library }: { library: StationLibraryState }) {
  return (
    <div className="flex flex-col gap-3">
      <label className="relative block">
        <span className="sr-only">Search stations by name</span>
        <LuSearch
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-b2c-text-muted"
          aria-hidden
        />
        <input
          type="search"
          value={library.search}
          onChange={(event) => library.setSearch(event.target.value)}
          placeholder="Search stations by name..."
          className={cn(b2cInputBase, "pl-9")}
        />
      </label>

      <AsyncBoundary state={library.exams}>
        {(exams) => (
          <div className="flex flex-wrap gap-2">
            <ExamChip
              active={library.examCode === null}
              onClick={() => library.setExamCode(null)}
            >
              All exams
            </ExamChip>
            {exams.map((exam) => (
              <ExamChip
                key={exam.id}
                active={library.examCode === exam.code}
                onClick={() => library.setExamCode(exam.code)}
              >
                {exam.name}
              </ExamChip>
            ))}
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

function ExamChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "border-accent bg-accent text-ink-inverse"
          : "border-border bg-surface text-ink-muted hover:border-border-strong hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}
