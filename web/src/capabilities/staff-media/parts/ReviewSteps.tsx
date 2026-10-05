"use client";

import { Alert, Badge, Button, FoldSection, Textarea } from "@/foundation/ui";
import {
  isChecked,
  reviewOf,
  scriptGroups,
  setScriptLine,
  voicedUrl,
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

/** The voiced result, playable where it was made: the deck's video, or the audio. */
function Recording({ kind, url }: { kind: string; url: string }) {
  return kind === "slide_deck" ? (
    // eslint-disable-next-line jsx-a11y/media-has-caption -- staff preview of the voiced deck
    <video
      key={url}
      src={url}
      controls
      preload="metadata"
      className="w-full max-w-3xl rounded-panel border border-border bg-black"
    />
  ) : (
    // eslint-disable-next-line jsx-a11y/media-has-caption -- staff preview of the voiced audio
    <audio key={url} src={url} controls preload="metadata" className="w-full max-w-xl" />
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
  const recording = voiced ? voicedUrl(kind, content) : "";

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
        <Alert tone="success">Voiced. Watch or listen below, then publish.</Alert>
      ) : null}
      {recording ? <Recording kind={kind} url={recording} /> : null}
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
