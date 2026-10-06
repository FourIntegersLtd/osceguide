/** Where a rubric version stands on its way to marking: the steps, and the one thing to do next. */

import type { RailStep } from "@/foundation/ui";

export type RubricStepId = "draft" | "preview" | "publish";

export type RubricState = {
  /** The version's status: draft, published or archived. */
  status: string;
  dirty: boolean;
  checking: boolean;
  problems: number;
  promptMissing: boolean;
};

/** Draft, preview, publish. "Used by an exam" is not known here, so it is not a step. */
export function rubricSteps(state: RubricState): RailStep<RubricStepId>[] {
  const live = state.status !== "draft";
  const previewReady = !state.checking && state.problems === 0 && !state.promptMissing;
  return [
    {
      id: "draft",
      label: "Draft",
      state: live || !state.dirty ? "done" : "attention",
      note: live ? "Saved" : state.dirty ? "Unsaved changes" : "Saved",
    },
    {
      id: "preview",
      label: "Preview",
      state: live || previewReady ? "done" : "todo",
      note: live
        ? "Checked"
        : state.checking
          ? "Checking…"
          : state.problems > 0
            ? `${state.problems} ${state.problems === 1 ? "problem" : "problems"}`
            : state.promptMissing
              ? "Needs instructions"
              : "No problems",
    },
    {
      id: "publish",
      label: "Publish",
      state: live ? "done" : "todo",
      note: live ? (state.status === "published" ? "Live" : "Archived") : "Not published",
    },
  ];
}

export type RubricNextAction = { id: "wait" | "fix" | "instructions" | "save" | "publish" | "none"; line: string };

export function rubricNextAction(state: RubricState): RubricNextAction {
  if (state.status !== "draft") {
    return { id: "none", line: "This version is read-only. Start a new draft to change it." };
  }
  if (state.checking) return { id: "wait", line: "Checking the latest edit…" };
  if (state.problems > 0) {
    return { id: "fix", line: `Fix ${state.problems} ${state.problems === 1 ? "problem" : "problems"} to publish.` };
  }
  if (state.promptMissing) {
    return { id: "instructions", line: "Add marking instructions on the Marking tab to publish." };
  }
  if (state.dirty) return { id: "save", line: "You have unsaved changes. Save them to publish." };
  return { id: "publish", line: "Looks right in the preview. Publish this version." };
}
