/** The edit screen's lock states in a hire workspace (board HireEditRotation); institution keeps its own copy. */
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

interface CircuitEditBlock {
  tone: "danger" | "warning";
  title: string;
  body: string;
  /** The button to the console, when the way on is to redo a station there. */
  console: string | null;
  /** A line under the alert when the screen is only looked at. */
  note: string | null;
}

export function circuitEditBlock(
  circuit: { editable?: boolean; edit_block?: string | null },
  w: AssessWords,
): CircuitEditBlock | null {
  if (!w.hiring || (circuit.editable !== false && !circuit.edit_block)) return null;
  if (circuit.edit_block === "consultation_in_progress") {
    return {
      tone: "warning",
      title: `A station is being taken in this ${w.circuit}`,
      body: "You can look, but your changes would overwrite theirs. Try again when they finish.",
      console: null,
      note: `The ${w.circuit} is shown read-only.`,
    };
  }
  return {
    tone: "danger",
    title: `This ${w.circuit} has started`,
    body: "Stations that have run cannot change. Use the console to redo a station.",
    console: "Open the console",
    note: null,
  };
}

export function circuitSaveLabel(locked: boolean, w: AssessWords): string {
  const base = w.hiring ? `Save ${w.circuit}` : "Save changes";
  return locked ? `${base} · locked` : base;
}
