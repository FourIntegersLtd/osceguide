"use client";

import { useMemo, useState } from "react";
import { Button } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { JsonField, formatJson, jsonProblem, parseJson } from "@/capabilities/authoring/parts/JsonField";
import { StructureBuilder } from "@/capabilities/authoring/parts/StructureBuilder";
import {
  blankStructure,
  parseStructure,
  type StationStructure,
} from "@/capabilities/authoring/parts/structureTypes";

export function StructureField({
  label,
  value,
  rows = 12,
  hint,
  onChange,
}: {
  label: string;
  value: string;
  rows?: number;
  hint?: string;
  onChange: (json: string) => void;
}) {
  const [raw, setRaw] = useState(false);
  const structure = useMemo(
    () => parseStructure(parseJson(value)) ?? blankStructure(),
    [value],
  );

  const setStructure = (next: StationStructure) => {
    onChange(formatJson(next));
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-osce-body font-semibold text-b2b-headline">{label}</span>
        <AuthoringButton variant="ghost" size="xs" onClick={() => setRaw((current) => !current)}>
          {raw ? "Visual editor" : "Raw JSON"}
        </AuthoringButton>
      </div>
      {hint ? <p className="text-xs text-b2b-mid">{hint}</p> : null}
      {raw ? (
        <JsonField label="" value={value} rows={rows} onChange={onChange} />
      ) : (
        <StructureBuilder value={structure} onChange={setStructure} />
      )}
      {!raw && jsonProblem(value) ? (
        <p className="text-xs text-red-600">Structure JSON is invalid — switch to raw JSON to fix.</p>
      ) : null}
    </div>
  );
}
