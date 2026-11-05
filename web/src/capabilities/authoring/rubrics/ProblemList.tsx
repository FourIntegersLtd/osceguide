"use client";

import { HiOutlineCheckCircle, HiOutlineExclamationTriangle } from "react-icons/hi2";
import { parsePath, pathText } from "@/capabilities/authoring/rubrics/jsonPath";
import { placeLabel, type Problem } from "@/capabilities/authoring/rubrics/problems";
import type { RubricStructure } from "@/capabilities/authoring/rubrics/rubricEdits";

/**
 * Bring the input a problem names into view.
 *
 * Inputs carry `data-path`; a problem about a whole list or card
 * (`sections[0].competencyFields`) finds that list's wrapper. When nothing
 * carries the exact path, the nearest enclosing path that does is used.
 */
export function revealPath(path: string): void {
  const segments = parsePath(path);
  for (let length = segments.length; length > 0; length -= 1) {
    const target = document.querySelector<HTMLElement>(`[data-path="${CSS.escape(pathText(segments.slice(0, length)))}"]`);
    if (!target) continue;
    target.scrollIntoView({ block: "center", behavior: "smooth" });
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
      target.focus({ preventScroll: true });
    }
    return;
  }
}

/**
 * Every problem the backend found in the draft, by where it is. Clicking one
 * opens the right tab and scrolls to the input; the same message is also
 * shown under that input.
 */
export function ProblemList({
  problems,
  structure,
  checking,
  onPick,
}: {
  problems: readonly Problem[];
  structure: RubricStructure;
  checking: boolean;
  onPick: (problem: Problem) => void;
}) {
  if (problems.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-osce-md border border-osce-border bg-osce-surface px-3 py-2 text-osce-meta text-ink-muted">
        <HiOutlineCheckCircle className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
        {checking ? "Checking…" : "None. Publishing is blocked while any are listed here, and each says what to fix."}
      </div>
    );
  }
  return (
    <div className="rounded-osce-md border border-osce-danger-border bg-osce-danger-bg p-3" aria-live="polite">
      <p className="flex items-center gap-2 text-osce-meta font-semibold text-osce-danger-text">
        <HiOutlineExclamationTriangle className="h-4 w-4 shrink-0" aria-hidden />
        {problems.length} {problems.length === 1 ? "problem" : "problems"} to fix before publishing
      </p>
      <ul className="mt-2 max-h-56 space-y-1 overflow-y-auto">
        {problems.map((problem, index) => (
          <li key={`${problem.path}-${index}`}>
            <button
              type="button"
              onClick={() => onPick(problem)}
              className="w-full rounded-osce-sm px-2 py-1 text-left hover:bg-osce-surface"
            >
              <span className="block text-osce-caption font-medium text-ink-muted">{placeLabel(structure, problem.path)}</span>
              <span className="block text-osce-meta text-ink">{problem.message}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
