"use client";

import { Select } from "@/foundation/ui";
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
  const { options, loading, error, reload } = useAuthoringExamCatalog();

  return (
    <>
    <Select
      id={id}
      value={value}
      required={required}
      onChange={(event) => onChange(event.target.value)}
      className={className ?? "mt-1"}
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
    {error ? (
      <p role="alert" className="mt-1 text-osce-caption text-danger">
        {error}{" "}
        <button type="button" onClick={reload} className="underline">
          Try again
        </button>
      </p>
    ) : null}
    </>
  );
}
