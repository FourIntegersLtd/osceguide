"use client";

import { useMemo } from "react";
import { getInputClassName } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listRubrics } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";

export interface ExamDraft {
  code: string;
  name: string;
  reading: string;
  simulation: string;
  attempts: string;
  partnerPilot: boolean;
  rubricVersionId: string;
}

/** The backend's own defaults, so a blank form creates a working exam. */
export const blankExam: ExamDraft = {
  code: "",
  name: "",
  reading: "120",
  simulation: "600",
  attempts: "3",
  partnerPilot: false,
  rubricVersionId: "",
};

/**
 * The exam form, shared by create and edit.
 *
 * Create and edit took the same seven fields in the old client and were two
 * components, which is how they came to disagree about the attempt limit's
 * default.
 */
export function ExamFields({
  value,
  onChange,
  codeDisabled = false,
}: {
  value: ExamDraft;
  onChange: (next: ExamDraft) => void;
  codeDisabled?: boolean;
}) {
  const scope = useAuthoringScope();
  const rubrics = useAsync((signal) => listRubrics(scope, {}, signal), [scope.base]);

  const versions = useMemo(
    () =>
      (rubrics.data?.items ?? []).flatMap((rubric) =>
        (rubric.versions ?? [])
          .filter((v) => v.status === "published")
          .map((v) => ({ id: v.id, label: `${rubric.title} · v${v.version}` })),
      ),
    [rubrics.data],
  );

  const set = (patch: Partial<ExamDraft>) => onChange({ ...value, ...patch });

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Code">
          <input
            value={value.code}
            disabled={codeDisabled}
            onChange={(e) => set({ code: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. finals"
          />
        </Field>
        <Field label="Name">
          <input
            value={value.name}
            onChange={(e) => set({ name: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
            placeholder="e.g. Final MB OSCE"
          />
        </Field>
        <Field label="Reading time (seconds)">
          <input
            type="number"
            value={value.reading}
            onChange={(e) => set({ reading: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
          />
        </Field>
        <Field label="Station time (seconds)">
          <input
            type="number"
            value={value.simulation}
            onChange={(e) => set({ simulation: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
          />
        </Field>
        <Field label="Attempts per station">
          <input
            type="number"
            value={value.attempts}
            onChange={(e) => set({ attempts: e.target.value })}
            className={`mt-1 ${getInputClassName()}`}
          />
        </Field>
        <Field label="Rubric version">
          <select
            value={value.rubricVersionId}
            onChange={(e) => set({ rubricVersionId: e.target.value })}
            className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 text-osce-body text-b2b-headline"
          >
            <option value="">None yet</option>
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <label className="flex cursor-pointer items-center gap-2 text-osce-body text-b2b-graphite">
        <input
          type="checkbox"
          checked={value.partnerPilot}
          onChange={(e) => set({ partnerPilot: e.target.checked })}
          className="h-4 w-4 rounded border-b2b-border"
        />
        Partner pilot
      </label>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-osce-body font-semibold text-b2b-headline">{label}</label>
      {children}
    </div>
  );
}
