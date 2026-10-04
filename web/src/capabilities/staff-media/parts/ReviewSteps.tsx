"use client";

import { useState } from "react";
import { Alert, Badge, Button, FoldSection, Input, Textarea } from "@/foundation/ui";
import {
  acceptSuggestion,
  dismissSuggestion,
  isChecked,
  needsRuling,
  reviewOf,
  scriptGroups,
  setScriptLine,
  type FactClaim,
  type FactVerdict,
  type ReviewStep,
  type ScriptChange,
  type ScriptGroup,
  type ScriptIssue,
  type StepId,
} from "@/capabilities/staff-media/content/review";

type Content = Record<string, unknown>;

type StepProps = {
  kind: string;
  content: Content;
  onChange: (content: Content) => void;
  /** True while a job runs, or while the form holds edits the server has not been sent. */
  locked: boolean;
  /** True while this step's own job runs, so its button says so. */
  working?: boolean;
};

const VERDICTS: Record<
  FactVerdict,
  { label: string; tone: "success" | "danger" | "warning" | "neutral" }
> = {
  supported: { label: "Supported", tone: "success" },
  contradicted: { label: "Contradicted", tone: "danger" },
  conflict: { label: "Sources disagree", tone: "warning" },
  not_found: { label: "No source found", tone: "warning" },
  not_checked: { label: "Not checked", tone: "neutral" },
};

const STATE_TONES = { todo: "neutral", attention: "warning", done: "success" } as const;

function when(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}

/** The four steps across the top: where the item stands, and which one is open. */
export function StepNav({
  steps,
  current,
  onSelect,
}: {
  steps: ReviewStep[];
  current: StepId;
  onSelect: (step: StepId) => void;
}) {
  return (
    <ol className="grid grid-cols-2 gap-2 lg:grid-cols-4" aria-label="Steps">
      {steps.map((step, index) => (
        <li key={step.id}>
          <button
            type="button"
            aria-current={step.id === current ? "step" : undefined}
            onClick={() => onSelect(step.id)}
            className={`flex w-full flex-col gap-1 rounded-panel border p-3 text-left ${
              step.id === current ? "border-accent" : "border-border"
            }`}
          >
            <span className="text-osce-body font-semibold text-ink">
              {index + 1}. {step.label}
            </span>
            <span>
              <Badge tone={STATE_TONES[step.state]}>{step.note}</Badge>
            </span>
          </button>
        </li>
      ))}
    </ol>
  );
}

function Claim({
  claim,
  onAccept,
  onDismiss,
}: {
  claim: FactClaim;
  onAccept: (wording: string) => void;
  onDismiss: () => void;
}) {
  const [wording, setWording] = useState(claim.suggestion?.new ?? "");
  const verdict = VERDICTS[claim.verdict] ?? VERDICTS.not_checked;
  const open = claim.suggestion && !claim.decision;

  return (
    <li className="flex flex-col gap-2 rounded-panel border border-border border-l-4 border-l-accent bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={verdict.tone}>{verdict.label}</Badge>
        {claim.slide !== null ? (
          <span className="text-osce-meta text-ink-subtle">Slide {claim.slide}</span>
        ) : null}
        {claim.decision ? (
          <Badge tone="neutral">
            {claim.decision === "accepted" ? "Correction made" : "Dismissed"}
          </Badge>
        ) : null}
      </div>
      <p className="text-osce-body text-ink">{claim.claim}</p>
      {claim.why ? <p className="text-osce-meta text-ink-subtle">{claim.why}</p> : null}
      {claim.evidence.map((evidence, index) => (
        <blockquote
          key={index}
          className="border-l-2 border-border pl-3 text-osce-meta text-ink-subtle"
        >
          “{evidence.quote}”
          <span className="mt-1 block text-ink">
            {evidence.url ? (
              <a href={evidence.url} target="_blank" rel="noreferrer" className="underline">
                {evidence.source}
              </a>
            ) : (
              evidence.source
            )}
            {evidence.section ? `, ${evidence.section}` : ""}
            {evidence.page !== null ? `, page ${evidence.page}` : ""}
          </span>
        </blockquote>
      ))}
      {open && claim.suggestion?.old ? (
        <div className="flex flex-col gap-2">
          <Input
            label={`Replace “${claim.suggestion.old}” with`}
            value={wording}
            onChange={(event) => setWording(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={!wording.trim()} onClick={() => onAccept(wording.trim())}>
              Accept correction
            </Button>
            <Button size="sm" variant="ghost" onClick={onDismiss}>
              Keep as written
            </Button>
          </div>
        </div>
      ) : null}
      {open && !claim.suggestion?.old ? (
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-osce-body text-ink">
            Suggested: {claim.suggestion?.new} (edit it in the draft)
          </p>
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Keep as written
          </Button>
        </div>
      ) : null}
      {!claim.suggestion && needsRuling(claim) ? (
        <div>
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            Keep as written
          </Button>
        </div>
      ) : null}
    </li>
  );
}

/** Step 2: each clinical claim against the guidelines. Only what needs a decision is shown first. */
export function FactsStep({
  content,
  onChange,
  locked,
  working = false,
  onCheck,
}: StepProps & { onCheck: () => void }) {
  const [showAll, setShowAll] = useState(false);
  const facts = reviewOf(content).facts;
  const claims = facts?.claims ?? [];
  const unsettled = claims.filter((claim) => claim.verdict !== "supported");
  const settled = claims.length - unsettled.length;
  const shown = showAll ? claims : unsettled;
  const toRule = claims.filter(needsRuling).length;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-osce-body text-ink">
        Every clinical claim in the draft is looked up in the guideline library, and on the clinical
        web where the library is silent. Nothing in your draft is changed unless you accept a
        correction.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Button size="sm" variant={facts ? "secondary" : "primary"} disabled={locked} isLoading={working} onClick={onCheck}>
          {working ? "Checking facts…" : facts ? "Check facts again" : "Check facts"}
        </Button>
        {facts ? (
          <span className="text-osce-meta text-ink-subtle">
            {claims.length} claims checked {when(facts.checked_at)}: {settled} supported,{" "}
            {unsettled.length} to read, {toRule} to resolve
          </span>
        ) : null}
      </div>
      {facts && unsettled.length === 0 ? (
        <Alert tone="success">Every claim is supported by a source. Go on to the script.</Alert>
      ) : null}
      {shown.length > 0 ? (
        <ul className="flex flex-col gap-3">
          {shown.map((claim) => (
            <Claim
              key={claim.id}
              claim={claim}
              onAccept={(wording) => onChange(acceptSuggestion(content, claim, wording))}
              onDismiss={() => onChange(dismissSuggestion(content, claim))}
            />
          ))}
        </ul>
      ) : null}
      {settled > 0 ? (
        <div>
          <Button size="sm" variant="ghost" onClick={() => setShowAll(!showAll)}>
            {showAll ? "Hide supported claims" : `Show the ${settled} supported claims`}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function Group({
  group,
  issues,
  changes,
  onEdit,
}: {
  group: ScriptGroup;
  issues: ScriptIssue[];
  changes: ScriptChange[];
  onEdit: (line: number, value: string) => void;
}) {
  return (
    <FoldSection
      title={group.label}
      defaultOpen={issues.length > 0}
      meta={
        <>
          {issues.length > 0 ? <Badge tone="warning">{issues.length} flagged</Badge> : null}
          {changes.length > 0 ? <Badge tone="neutral">{changes.length} corrected</Badge> : null}
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {group.lines.map((line, index) => {
          const number = index + 1;
          const flagged = issues.filter((issue) => issue.line === number);
          const changed = changes.filter((change) => change.line === number);
          return (
            <div key={index} className="flex flex-col gap-1">
              <Textarea
                aria-label={`${group.label}, line ${number}`}
                label={line.speaker ?? undefined}
                rows={2}
                value={line.text}
                onChange={(event) => onEdit(number, event.target.value)}
              />
              {flagged.map((issue, at) => (
                <Alert key={`issue-${at}`} tone="warning">
                  {issue.quote ? `“${issue.quote}”: ` : ""}
                  {issue.why}
                  {issue.fix ? (
                    <span className="mt-1 flex flex-wrap items-center gap-2">
                      <span>Suggested: {issue.fix}</span>
                      <Button size="sm" variant="ghost" onClick={() => onEdit(number, issue.fix)}>
                        Use this
                      </Button>
                    </span>
                  ) : null}
                </Alert>
              ))}
              {changed.map((change, at) => (
                <p key={`change-${at}`} className="text-osce-meta text-ink-subtle">
                  Corrected automatically: {change.why} It was: “{change.before}”
                </p>
              ))}
            </div>
          );
        })}
      </div>
    </FoldSection>
  );
}

/** Step 3: what will be said, written and read back against the draft. Flagged slides open first. */
export function ScriptStep({
  kind,
  content,
  onChange,
  locked,
  working = false,
  onWrite,
}: StepProps & { onWrite: (rewrite: boolean) => void }) {
  const script = reviewOf(content).script;
  const groups = scriptGroups(kind, content);
  const checked = isChecked(kind, content);
  const issues = script?.issues ?? [];
  const changes = script?.changes ?? [];
  const wholeDeck = issues.filter((issue) => issue.part === "deck");
  const within = <T extends { part: string; slide: number | null }>(
    entries: T[],
    group: ScriptGroup,
  ) => entries.filter((entry) => entry.part === group.part && entry.slide === group.slide);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-osce-body text-ink">
        The script is what the presenter will say. It is written from the draft, then read back
        line by line against it. No voice credits are used here.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Button
          size="sm"
          variant={checked ? "secondary" : "primary"}
          disabled={locked}
          isLoading={working}
          onClick={() => onWrite(false)}
        >
          {working
            ? groups.length === 0
              ? "Writing script…"
              : "Checking script…"
            : groups.length === 0
              ? "Write script and check"
              : "Check script"}
        </Button>
        {groups.length > 0 ? (
          <Button size="sm" variant="ghost" disabled={locked} onClick={() => onWrite(true)}>
            Rewrite the whole script
          </Button>
        ) : null}
        {script?.checked_at ? (
          <span className="text-osce-meta text-ink-subtle">
            Checked {when(script.checked_at)}: {issues.length} flagged, {changes.length} corrected
            automatically
          </span>
        ) : null}
      </div>
      {groups.length > 0 && !checked ? (
        <Alert tone="warning">
          The script has changed since it was last checked. Save, then check it again before
          voicing.
        </Alert>
      ) : null}
      {checked && issues.length === 0 ? (
        <Alert tone="success">
          Checked, with nothing flagged. Open any slide to read or edit its lines.
        </Alert>
      ) : null}
      {wholeDeck.map((issue, index) => (
        <Alert key={index} tone="warning">
          {issue.why}
        </Alert>
      ))}
      {groups.map((group, index) => (
        <Group
          key={index}
          group={group}
          issues={within(issues, group)}
          changes={within(changes, group)}
          onEdit={(line, value) => onChange(setScriptLine(content, group, line, value))}
        />
      ))}
    </div>
  );
}

/** Step 4: the one click that spends voice credits, with what stands behind it. */
export function VoiceStep({
  kind,
  content,
  locked,
  working = false,
  steps,
  onVoice,
}: Omit<StepProps, "onChange"> & { steps: ReviewStep[]; onVoice: () => void }) {
  const checked = isChecked(kind, content);
  const before = steps.filter((step) => step.id !== "voice");
  const voiced = steps.find((step) => step.id === "voice")?.state === "done";

  return (
    <div className="flex flex-col gap-4">
      <p className="text-osce-body text-ink">
        Voicing records the checked script{kind === "slide_deck" ? " and builds the video" : ""}.
        This is the only step that uses voice credits.
      </p>
      <ul className="flex flex-col gap-2">
        {before.map((step) => (
          <li key={step.id} className="flex flex-wrap items-center gap-2 text-osce-body text-ink">
            <Badge tone={STATE_TONES[step.state]}>{step.note}</Badge>
            {step.label}
          </li>
        ))}
      </ul>
      {!checked ? (
        <Alert tone="info">Voicing unlocks once the script in step 3 has been checked.</Alert>
      ) : null}
      {voiced ? (
        <Alert tone="success">Voiced. Preview it in the draft, then publish.</Alert>
      ) : null}
      <div>
        <Button size="sm" disabled={locked || !checked} isLoading={working} onClick={onVoice}>
          {working
            ? kind === "slide_deck"
              ? "Voicing and building the video…"
              : "Voicing…"
            : voiced
              ? "Voice again"
              : "Approve and voice"}
        </Button>
      </div>
    </div>
  );
}
