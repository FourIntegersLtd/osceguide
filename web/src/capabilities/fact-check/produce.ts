import { record, records } from "@/capabilities/fact-check/facts";

/** The step a failure is kept under in a review, as staff read it. */
export const ERROR_STEPS: Record<string, string> = {
  facts: "fact check",
  script: "script check",
  produce: "agent run",
};

/** What the agent was asked to produce the material from: a topic, notes or a pasted case. */
export type ProduceBrief = { brief: string };

/** The agent's last run over the material, as it saves it after every step. */
export type ProduceRun = {
  steps: { at: string; tool: string; summary: string }[];
  tokens: number;
  /** Absent while it runs; then "finished", "stopped", or the limit it reached. */
  outcome: string | null;
  summary: string;
  /** What it changed and what it left for staff to decide. */
  open: string[];
  stop: boolean;
};

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function briefOf(value: unknown): ProduceBrief | null {
  const brief = record(value);
  // A run started before the brief and the source case were one box kept the case apart.
  return brief
    ? {
        brief: [text(brief.brief), text(brief.source_text)]
          .filter((part) => part.trim())
          .join("\n\n"),
      }
    : null;
}

export function runOf(value: unknown): ProduceRun | null {
  const run = record(value);
  if (!run) return null;
  return {
    steps: records(run.steps).map((step) => ({
      at: text(step.at),
      tool: text(step.tool),
      summary: text(step.summary),
    })),
    tokens: typeof run.tokens === "number" ? run.tokens : 0,
    outcome: text(run.outcome) || null,
    summary: text(run.summary),
    open: Array.isArray(run.open) ? run.open.map(String) : [],
    stop: run.stop === true,
  };
}
