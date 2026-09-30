"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Problem } from "@/capabilities/authoring/rubrics/problems";
import type { RubricStructure } from "@/capabilities/authoring/rubrics/rubricEdits";

/**
 * What every editor inside the rubric builder reads: the draft structure, the
 * one way to change it, the backend's current problems and whether the
 * version may be edited at all.
 *
 * The structure is deep (sections hold competencies hold fields hold fields),
 * so passing these four through every level as props would be most of the
 * code. Each editor instead names the path it edits and asks this context.
 */
export interface RubricBuilderContextValue {
  structure: RubricStructure;
  /** Apply one edit. Takes a function so two quick edits never overwrite each other. */
  edit: (change: (structure: RubricStructure) => RubricStructure) => void;
  problems: readonly Problem[];
  /** A published or archived version, or another owner's rubric: shown, never changed. */
  readOnly: boolean;
}

const RubricBuilderContext = createContext<RubricBuilderContextValue | null>(null);

export function RubricBuilderProvider({ value, children }: { value: RubricBuilderContextValue; children: ReactNode }) {
  return <RubricBuilderContext.Provider value={value}>{children}</RubricBuilderContext.Provider>;
}

export function useRubricBuilder(): RubricBuilderContextValue {
  const value = useContext(RubricBuilderContext);
  if (!value) throw new Error("useRubricBuilder is used outside RubricBuilderProvider.");
  return value;
}
