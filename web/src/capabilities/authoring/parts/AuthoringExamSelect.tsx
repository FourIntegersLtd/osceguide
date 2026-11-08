"use client";

import { Select } from "@/foundation/ui";
import { LoadError } from "@/capabilities/authoring/parts/LoadError";
import { useAuthoringExamCatalog } from "@/capabilities/authoring/parts/useAuthoringExamCatalog";

/** The exam picker. `className` lays out its wrapper only; the control itself is styled by `Select`. */
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
  const { options, loading, error, reload } = useAuthoringExamCatalog();

  return (
    <>
      <Select
        id={id}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className={className}
      >
        {allowEmpty ? (
          <option value="">
            {loading ? "Loading exams…" : error ? "Exams could not be loaded" : emptyLabel}
          </option>
        ) : null}
        {options.map((exam) => (
          <option key={exam.code} value={exam.code}>
            {exam.label}
          </option>
        ))}
      </Select>
      {error ? <LoadError message={error} onRetry={reload} /> : null}
    </>
  );
}
