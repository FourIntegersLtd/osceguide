"use client";

import { useMemo } from "react";
import { Badge, Card, cn } from "@/foundation/ui";
import {
  RAG_LABEL,
  normaliseFeedback,
  ragTally,
  type CompetencyGroup,
  type Rag,
} from "@/capabilities/feedback/model";

const RAG_TONE: Record<Rag, "danger" | "warning" | "success"> = {
  R: "danger",
  A: "warning",
  G: "success",
};

/**
 * One scored attempt, rendered.
 *
 * The same component shows a consumer their practice feedback and a supervisor
 * the machine's view beside their own marking. `readOnly` is the only
 * difference, and a reviewer's controls are composed around this rather than
 * forking it — two renderers is how the two clients came to disagree about
 * what a grade meant.
 */
export function FeedbackView({
  payload,
  className,
}: {
  payload: Record<string, unknown>;
  className?: string;
}) {
  const feedback = useMemo(() => normaliseFeedback(payload), [payload]);
  const tally = useMemo(() => ragTally(feedback.groups), [feedback.groups]);

  if (feedback.groups.length === 0 && feedback.priorities.length === 0) {
    return (
      <Card>
        <p className="text-sm text-ink-muted">
          This attempt has no feedback recorded. If it was just completed, scoring may still be
          running.
        </p>
      </Card>
    );
  }

  return (
    <div className={cn("flex flex-col gap-5", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {(["G", "A", "R"] as const).map((grade) => (
          <Badge key={grade} tone={RAG_TONE[grade]}>
            {tally[grade]} {RAG_LABEL[grade].toLowerCase()}
          </Badge>
        ))}
      </div>

      {feedback.priorities.length > 0 && (
        <Card title="Work on these first">
          <ol className="flex flex-col gap-4">
            {feedback.priorities.map((priority, index) => (
              <li key={`${priority.area}-${index}`} className="flex flex-col gap-1">
                <p className="text-sm font-semibold text-ink">{priority.area}</p>
                {priority.currentLevel && (
                  <p className="text-xs uppercase tracking-wide text-ink-subtle">
                    {priority.currentLevel}
                  </p>
                )}
                {priority.steps.length > 0 && (
                  <ul className="ml-4 list-disc text-sm text-ink-muted">
                    {priority.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ul>
                )}
                {priority.expectedOutcome && (
                  <p className="text-sm text-ink-muted">{priority.expectedOutcome}</p>
                )}
              </li>
            ))}
          </ol>
        </Card>
      )}

      {feedback.groups.map((group) => (
        <GroupCard key={group.key} group={group} />
      ))}

      {feedback.analysis.map((section) => (
        <Card key={section.label} title={section.label}>
          <p className="whitespace-pre-wrap text-sm text-ink-muted">{section.body}</p>
        </Card>
      ))}
    </div>
  );
}

function GroupCard({ group }: { group: CompetencyGroup }) {
  return (
    <Card
      title={group.label}
      actions={group.score ? <Badge tone={RAG_TONE[group.score]}>{RAG_LABEL[group.score]}</Badge> : null}
    >
      <div className="flex flex-col gap-4">
        <Narrative label="What went well" items={group.strengths} />
        <Narrative label="What to improve" items={group.improvements} />
        <Narrative label="Try this next" items={group.actions} />

        <ul className="divide-y divide-border rounded-control border border-border">
          {group.competencies.map((competency) => (
            <li key={competency.key} className="flex flex-col gap-1 px-3 py-2.5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-ink">{competency.label}</p>
                {competency.score ? (
                  <Badge tone={RAG_TONE[competency.score]}>{competency.score}</Badge>
                ) : (
                  <Badge tone="neutral">Not scored</Badge>
                )}
              </div>
              {competency.explanation && (
                <p className="text-sm text-ink-muted">{competency.explanation}</p>
              )}
              {competency.quote && (
                <p className="border-l-2 border-border-strong pl-2 text-sm italic text-ink-subtle">
                  “{competency.quote}”
                </p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}

function Narrative({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-subtle">{label}</p>
      <ul className="ml-4 list-disc text-sm text-ink-muted">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
