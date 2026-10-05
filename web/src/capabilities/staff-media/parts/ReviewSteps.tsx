"use client";

import { Alert, Badge, Button, FoldSection, Textarea } from "@/foundation/ui";
import {
  isChecked,
  reviewOf,
  scriptGroups,
  setScriptLine,
  type ScriptChange,
  type ScriptGroup,
  type ScriptIssue,
} from "@/capabilities/staff-media/content/review";
import {
  scriptStatus,
  voicedUrl,
  type ReviewStep,
} from "@/capabilities/staff-media/content/steps";

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

function Group({
  group,
  issues,
  changes,
  rewritten,
  onEdit,
}: {
  group: ScriptGroup;
  issues: ScriptIssue[];
  changes: ScriptChange[];
  rewritten: boolean;
  onEdit: (line: number, value: string) => void;
}) {
  return (
    <FoldSection
      title={group.label}
      defaultOpen={issues.length > 0 || rewritten}
      meta={
        <>
          {rewritten ? <Badge tone="info">Rewritten, read before voicing</Badge> : null}
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
      <p className="text-osce-meta text-ink-subtle">
        What the presenter will say, read back line by line against the draft. No voice credits are
        used here.
      </p>
      <div className="flex flex-wrap items-center gap-3">
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
          Changed since its last check. A saved change to the draft rewrites and checks the lines it
          touches by itself.
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
          rewritten={group.part === "slide" && group.slide !== null && Boolean(script?.rewritten.includes(group.slide))}
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

/** Step 4: the recording, once made. Voicing itself starts from the next-step bar. */
export function VoiceStep({
  kind,
  content,
  locked,
  working = false,
  voiced,
  onVoice,
}: Omit<StepProps, "onChange"> & { voiced: boolean; onVoice: () => void }) {
  const script = scriptStatus(kind, content);
  const recording = voiced ? voicedUrl(kind, content) : "";

  return (
    <div className="flex flex-col gap-4">
      <p className="text-osce-meta text-ink-subtle">
        Records the checked script{kind === "slide_deck" ? " and builds the video" : ""}. The only
        step that uses voice credits.
      </p>
      {script === "unwritten" || script === "unchecked" ? (
        <Alert tone="info">Voicing unlocks once the script has been checked.</Alert>
      ) : null}
      {script === "changed" ? (
        <Alert tone="info">The script changed since it was voiced. Check it before voicing again.</Alert>
      ) : null}
      {recording ? <Recording kind={kind} url={recording} /> : null}
      {voiced ? (
        <div>
          <Button
            size="sm"
            variant="ghost"
            disabled={locked || script !== "checked"}
            isLoading={working}
            onClick={onVoice}
          >
            {working ? "Voicing…" : "Voice again"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

/** Step 5: what stands behind the item before learners see it. Publishing starts from the bar. */
export function PublishStep({ steps }: { steps: ReviewStep[] }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-osce-meta text-ink-subtle">
        Learners see it once it is published. Each step below can still be revisited.
      </p>
      <ul className="flex flex-col gap-2">
        {steps
          .filter((step) => step.id !== "publish")
          .map((step) => (
            <li key={step.id} className="flex flex-wrap items-center gap-2 text-osce-body text-ink">
              <Badge tone={STATE_TONES[step.state]}>{step.note}</Badge>
              {step.label}
            </li>
          ))}
      </ul>
    </div>
  );
}
