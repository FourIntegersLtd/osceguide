"use client";

import { getInputClassName } from "@/foundation/ui";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";

export function AuthoringExamSelect({
  id,
  value,
  onChange,
  required,
  allowEmpty = true,
  emptyLabel = "Select an exam…",
  className,
}: {
  id?: string;
  value: string;
  onChange: (code: string) => void;
  required?: boolean;
  allowEmpty?: boolean;
  emptyLabel?: string;
  className?: string;
}) {
  const { options, loading } = useAuthoringExamCatalog();

  return (
    <select
      id={id}
      value={value}
      required={required}
      onChange={(event) => onChange(event.target.value)}
      className={className ?? `mt-1 w-full ${getInputClassName()}`}
    >
      {allowEmpty ? (
        <option value="">{loading ? "Loading exams…" : emptyLabel}</option>
      ) : null}
      {options.map((exam) => (
        <option key={exam.code} value={exam.code}>
          {exam.label}
        </option>
      ))}
    </select>
  );
}
