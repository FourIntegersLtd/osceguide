"use client";

import { getInputClassName } from "@/foundation/ui";
import { AuthoringExamSelect } from "@/capabilities/authoring/parts/AuthoringExamSelect";

/** The labelled exam picker for an item; empty is any exam. */
export function AuthoringExamField({
  value,
  onChange,
}: {
  value: string;
  onChange: (code: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-osce-meta font-medium text-ink-muted">Exam</span>
      <AuthoringExamSelect
        value={value}
        onChange={onChange}
        allowEmpty
        emptyLabel="Any exam"
        className={getInputClassName()}
      />
    </label>
  );
}
