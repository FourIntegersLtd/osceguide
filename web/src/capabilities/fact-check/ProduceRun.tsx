"use client";

import { useState } from "react";
import { Badge, Button, Panel, Textarea } from "@/foundation/ui";
import type {
  ProduceBrief,
  ProduceRun,
} from "@/capabilities/fact-check/produce";

const OUTCOMES: Record<string, string> = {
  finished: "Finished",
  stopped: "Stopped",
  time: "Ran out of time",
  tokens: "Reached its token budget",
  turns: "Reached its step limit",
  silent: "Stopped answering",
};

/** The brief and source case the agent produces the material from, and the button that starts it. */
export function ProduceForm({
  brief,
  hint,
  locked,
  working,
  primary = false,
  onProduce,
}: {
  brief: ProduceBrief | null;
  /** What the agent will do, for the person about to start it. */
  hint: string;
  locked: boolean;
  working: boolean;
  /** Producing is the next step, so this is the screen's one primary button. */
  primary?: boolean;
  onProduce: (brief: string) => void;
}) {
  const [text, setText] = useState(brief?.brief ?? "");
  return (
    <div className="flex flex-col gap-3">
      <Textarea
        label="What should it cover?"
        hint={`A topic, your notes or a case pasted whole. ${hint}`}
        rows={8}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button
        variant={primary ? "primary" : "secondary"}
        size="sm"
        className="w-fit"
        disabled={locked || text.trim().length < 8}
        isLoading={working}
        onClick={() => onProduce(text.trim())}
      >
        {working ? "Producing…" : "Produce"}
      </Button>
    </div>
  );
}

/** What the agent is doing or did: its steps, what it changed and left, and what it used. */
export function RunLog({
  run,
  running,
  stopping,
  onStop,
}: {
  run: ProduceRun;
  running: boolean;
  stopping: boolean;
  onStop: () => void;
}) {
  const outcome = running
    ? null
    : (run.outcome && (OUTCOMES[run.outcome] ?? run.outcome)) || "Ended";
  return (
    <Panel
      title="Agent run"
      description={`${run.steps.length} steps · ${run.tokens.toLocaleString()} tokens`}
      padding="sm"
    >
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {running ? (
            <>
              <Badge tone="warning">
                {run.stop ? "Stopping after this step" : "Working"}
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                disabled={run.stop || stopping}
                isLoading={stopping}
                onClick={onStop}
              >
                Stop
              </Button>
            </>
          ) : (
            <Badge tone={run.outcome === "finished" ? "success" : "warning"}>
              {outcome}
            </Badge>
          )}
        </div>
        {run.summary ? (
          <p className="text-osce-body text-ink">{run.summary}</p>
        ) : null}
        {run.open.length ? (
          <div className="flex flex-col gap-1">
            <p className="text-osce-meta font-medium text-ink-muted">
              Changed or left for you
            </p>
            <ul className="list-disc pl-5 text-osce-meta text-ink">
              {run.open.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {run.steps.length ? (
          <details open={running}>
            <summary className="cursor-pointer text-osce-meta text-ink-subtle">
              Steps
            </summary>
            <ol className="mt-2 flex flex-col gap-1.5">
              {run.steps.map((step, index) => (
                <li
                  key={`${step.at}-${index}`}
                  className="text-osce-caption text-ink-subtle"
                >
                  <span className="font-medium text-ink">{step.tool}</span>{" "}
                  {step.summary.split("\n")[0]}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </div>
    </Panel>
  );
}
