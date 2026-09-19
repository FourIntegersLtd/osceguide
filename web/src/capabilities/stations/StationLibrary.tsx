"use client";

import { useState } from "react";
import { LuStethoscope } from "react-icons/lu";
import { AsyncBoundary, Badge, PageHeader, cn } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { browseLibrary, listExams, type LibraryStation } from "@/capabilities/stations/api";

/**
 * Browse the station library.
 *
 * `onPick` is how a surface uses this for its own purpose without the library
 * learning about it: Train passes "add to my mock", Assess passes "put this on
 * the circuit", and the component itself has no opinion.
 */
export function StationLibrary({
  onPick,
  pickLabel = "Select",
  selectedVersionIds,
}: {
  onPick?: (station: LibraryStation) => void;
  pickLabel?: string;
  selectedVersionIds?: ReadonlySet<string>;
}) {
  const [examCode, setExamCode] = useState<string | null>(null);
  const exams = useAsync((signal) => listExams(signal), []);
  const stations = useAsync((signal) => browseLibrary({ examCode, limit: 100 }, signal), [examCode]);

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Station library"
        description="Every scenario published for the exams you have access to."
      />

      <AsyncBoundary state={exams}>
        {(page) => (
          <div className="flex flex-wrap gap-2">
            <ExamChip active={examCode === null} onClick={() => setExamCode(null)}>
              All exams
            </ExamChip>
            {page.items.map((exam) => (
              <ExamChip
                key={exam.id}
                active={examCode === exam.code}
                onClick={() => setExamCode(exam.code)}
              >
                {exam.name}
              </ExamChip>
            ))}
          </div>
        )}
      </AsyncBoundary>

      <AsyncBoundary
        state={stations}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No stations here yet",
          description: "Published stations for this exam will appear here.",
        }}
      >
        {(page) => (
          <ul className="divide-y divide-border rounded-panel border border-border bg-surface">
            {page.items.map((station) => (
              <li
                key={station.version_id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <LuStethoscope className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{station.title}</p>
                    <p className="text-xs text-ink-subtle">Version {station.version}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone="accent">{station.exam_code.toUpperCase()}</Badge>
                  {onPick && (
                    <button
                      type="button"
                      onClick={() => onPick(station)}
                      disabled={selectedVersionIds?.has(station.version_id)}
                      className="rounded-control border border-border-strong px-3 py-1 text-sm font-medium text-ink hover:bg-surface-raised disabled:cursor-not-allowed disabled:text-ink-subtle"
                    >
                      {selectedVersionIds?.has(station.version_id) ? "Added" : pickLabel}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
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
