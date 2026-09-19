"use client";

import { useMemo } from "react";
import type { Json } from "@/capabilities/authoring/api";

/**
 * A structured field, edited as JSON.
 *
 * Station content, a template's structure, a feedback template's field
 * selection and a rubric's structure and pacing are all open objects on the
 * backend — their shape is the exam's, not the platform's. The retiring client
 * had the same textareas behind its builder, and the builder only ever wrote
 * what a person could also type here.
 *
 * Invalid JSON is reported under the field and the commit button is disabled,
 * rather than being discovered as a 422 after the request.
 */
export function JsonField({
  label,
  hint,
  value,
  rows = 10,
  onChange,
}: {
  label: string;
  hint?: string;
  value: string;
  rows?: number;
  onChange: (next: string) => void;
}) {
  const problem = useMemo(() => jsonProblem(value), [value]);

  return (
    <div>
      <label className="block text-osce-body font-semibold text-b2b-headline">{label}</label>
      {hint ? <p className="mt-0.5 text-osce-caption text-b2b-mid">{hint}</p> : null}
      <textarea
        value={value}
        rows={rows}
        spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-b2b-border bg-white px-3 py-2 font-mono text-osce-caption text-b2b-headline focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle"
      />
      {problem ? <p className="mt-1 text-osce-caption text-b2b-danger">{problem}</p> : null}
    </div>
  );
}

/** The parse failure to show, or null when the text is a JSON object. */
export function jsonProblem(value: string): string | null {
  const text = value.trim();
  if (!text) return "This cannot be empty. Use {} for nothing.";
  try {
    const parsed: unknown = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return "This has to be a JSON object.";
    }
    return null;
  } catch (cause) {
    return cause instanceof Error ? cause.message : "That is not valid JSON.";
  }
}

export function parseJson(value: string): Json {
  return JSON.parse(value.trim()) as Json;
}

export function formatJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}
