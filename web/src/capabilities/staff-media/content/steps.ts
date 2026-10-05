/**
 * Where a spoken item stands on its way from a brief to learners: the five
 * steps, and the one thing to do next.
 */

import type { RailStep } from "@/foundation/ui";
import { checkingLine, draftStep, factsStep, records } from "@/capabilities/fact-check/facts";
import { isChecked, reviewOf, scriptGroups } from "@/capabilities/staff-media/content/review";

type Content = Record<string, unknown>;

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export type StepId = "draft" | "facts" | "script" | "voice" | "publish";

export type ReviewStep = RailStep<StepId>;

const VOICED_FIELD: Record<string, string> = {
  slide_deck: "final_video_url",
  summary: "podcast_url",
  podcast: "audio_url",
};

/** Where the voiced recording (the deck's video, or the audio) lives, once voicing has run. */
export function voicedUrl(kind: string, content: Content): string {
  return text(content[VOICED_FIELD[kind] ?? ""]).trim();
}

function hasDraft(kind: string, content: Content): boolean {
  if (kind === "slide_deck") return records(content.slides).length > 0;
  return Object.entries(content).some(
    ([name, value]) =>
      name !== "review" &&
      name !== "status" &&
      !name.endsWith("_url") &&
      (Array.isArray(value) ? value.length > 0 : text(value).trim() !== ""),
  );
}

/** Whether voicing has run and finished, so the recording says what the item says. */
function isVoiced(kind: string, content: Content): boolean {
  const status = text(content.status);
  return voicedUrl(kind, content) !== "" && (status === "" || status === "completed");
}

/**
 * Where the spoken lines stand: `changed` was voiced and then edited; `unrecorded` was voiced
 * with no script check on record (imported, or published before checks were kept).
 */
type ScriptStatus = "unwritten" | "checked" | "unchecked" | "changed" | "unrecorded";

export function scriptStatus(kind: string, content: Content): ScriptStatus {
  if (scriptGroups(kind, content).length === 0) return "unwritten";
  if (isChecked(kind, content)) return "checked";
  if (!isVoiced(kind, content)) return "unchecked";
  return reviewOf(content).script ? "changed" : "unrecorded";
}

const SCRIPT_STEP: Record<ScriptStatus, Pick<ReviewStep, "state" | "note">> = {
  unwritten: { state: "todo", note: "Not written" },
  checked: { state: "done", note: "Checked" },
  unchecked: { state: "attention", note: "Needs checking" },
  changed: { state: "attention", note: "Changed since voicing" },
  unrecorded: { state: "todo", note: "Not recorded" },
};

/** The five steps from a brief to a published item, each with where it stands. */
export function reviewSteps(kind: string, content: Content, published = false): ReviewStep[] {
  const review = reviewOf(content);
  const script = scriptStatus(kind, content);
  const flagged = review.script?.issues.length ?? 0;
  const voiced = isVoiced(kind, content);
  return [
    draftStep(hasDraft(kind, content)),
    // Voiced with no check on record may well have been checked: say the record is missing.
    factsStep(review.facts, voiced ? "Not recorded" : "Not checked"),
    {
      id: "script",
      label: "Script",
      ...SCRIPT_STEP[script],
      ...(script === "checked" && flagged > 0 ? { note: `Checked, ${flagged} flagged` } : {}),
    },
    {
      id: "voice",
      label: "Voice",
      state: voiced ? "done" : "todo",
      note: voiced ? "Voiced" : "Not voiced",
    },
    {
      id: "publish",
      label: "Publish",
      state: published ? "done" : "todo",
      note: published ? "Live" : "Not published",
    },
  ];
}

/** The one thing to do now. `run` actions are started from the bar; the rest are done in a step. */
type NextActionId =
  | "save"
  | "wait"
  | "produce"
  | "check-facts"
  | "rule"
  | "write-script"
  | "check-script"
  | "voice"
  | "publish"
  | "preview";

export type NextAction = {
  id: NextActionId;
  /** The step this belongs to, which the screen opens on. */
  step: StepId;
  /** Where the item stands, in one line. */
  line: string;
};

const JOBS: Record<string, Pick<NextAction, "step" | "line">> = {
  producing: { step: "draft", line: "The agent is producing this. It stops before voicing." },
  checking_facts: { step: "facts", line: checkingLine(null) },
  writing_script: { step: "script", line: "Writing and checking the script…" },
};

/** What to do next with an item, from what is stored and whether the form is ahead of it. */
export function nextAction(
  kind: string,
  content: Content,
  { published, unsaved }: { published: boolean; unsaved: boolean },
): NextAction {
  const status = text(content.status);
  const review = reviewOf(content);
  if (JOBS[status] || status.startsWith("generating")) {
    const job = JOBS[status] ?? { step: "voice", line: "Voicing. This page updates when it finishes." };
    return {
      id: "wait",
      step: job.step,
      line: status === "checking_facts" ? checkingLine(review.facts) : job.line,
    };
  }
  const steps = reviewSteps(kind, content, published);
  const open = steps.find((step) => step.state !== "done");
  const step = open?.id ?? "publish";
  if (unsaved) return { id: "save", step, line: "You have unsaved changes. Save them before the next step." };
  if (!hasDraft(kind, content)) {
    return { id: "produce", step: "draft", line: "Say what to teach below and the agent drafts it." };
  }
  if (open?.id === "facts") {
    if (review.facts) {
      return { id: "rule", step: "facts", line: `${open.note}: each claim needs your decision.` };
    }
    // Opened on the draft, so it is read before it is checked.
    return {
      id: "check-facts",
      step: review.script ? "facts" : "draft",
      line: "Read the draft, then check its facts against the guidelines.",
    };
  }
  if (open?.id === "script") {
    const script = scriptStatus(kind, content);
    return script === "unwritten"
      ? { id: "write-script", step, line: "Facts settled. Write the script the presenter will say." }
      : {
          id: "check-script",
          step,
          line:
            script === "changed"
              ? "The script changed since it was voiced. Check it again."
              : "Check the script before voicing.",
        };
  }
  if (open?.id === "voice") {
    return { id: "voice", step, line: "Checked and ready to record. Voicing uses voice credits." };
  }
  if (open?.id === "publish") {
    return { id: "publish", step, line: "Voiced. Watch it through, then publish." };
  }
  return { id: "preview", step, line: "Live for learners." };
}

/** A draft's place in the pipeline, for the list: the open step and how it stands. */
export function stageOf(kind: string, content: Content): string {
  if (nextAction(kind, content, { published: false, unsaved: false }).id === "wait") return "Working…";
  const open = reviewSteps(kind, content).find((step) => step.state !== "done");
  return open ? `${open.label}: ${open.note}` : "";
}
