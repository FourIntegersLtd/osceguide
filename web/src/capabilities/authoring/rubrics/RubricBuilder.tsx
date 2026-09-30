"use client";

import { useMemo, useState } from "react";
import { Alert, B2CSegmentedTabs, Panel } from "@/foundation/ui";
import { PlatformError } from "@/foundation/platform-client";
import {
  draftRubricInstructions,
  publishRubricVersion,
  type AuthoringScope,
  type Rubric,
  type RubricVersion,
  type TrialMarkRequest,
} from "@/capabilities/authoring/api";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { RubricBuilderProvider } from "@/capabilities/authoring/rubrics/builderContext";
import type { RubricDashboardPreview } from "@/capabilities/authoring/rubrics/dashboardSlot";
import { DisplayPanel } from "@/capabilities/authoring/rubrics/DisplayPanel";
import { applyInstructionSuggestions } from "@/capabilities/authoring/rubrics/draftInstructions";
import { MarkingPanel } from "@/capabilities/authoring/rubrics/MarkingPanel";
import { PreviewPane } from "@/capabilities/authoring/rubrics/PreviewPane";
import { ProblemList, revealPath } from "@/capabilities/authoring/rubrics/ProblemList";
import { problemsFromDetails, tabFor, type BuilderTab, type Problem } from "@/capabilities/authoring/rubrics/problems";
import { previewInputs, trialInputs } from "@/capabilities/authoring/rubrics/previewModel";
import { RatingPanel } from "@/capabilities/authoring/rubrics/RatingPanel";
import { SectionList } from "@/capabilities/authoring/rubrics/SectionEditor";
import { TrialPanel } from "@/capabilities/authoring/rubrics/TrialPanel";
import { useRubricDraft } from "@/capabilities/authoring/rubrics/useRubricDraft";
import { useTrialMark } from "@/capabilities/authoring/rubrics/useTrialMark";

type EditorTab = BuilderTab | "marking";

/**
 * One rubric version, edited with its preview beside it.
 *
 * Left: the tabs an author works through — the parts of the result, the
 * rating, how results are summed up, and the marking prompt. Right: the
 * backend's problems, the candidate's feedback page and dashboard drawn from
 * a sample result, and a trial mark. Save writes the draft; Publish is only
 * offered once it is saved and the backend finds nothing wrong with it.
 */
export function RubricBuilder({
  scope,
  rubric,
  version,
  readOnly,
  dashboardPreview,
  onPublished,
}: {
  scope: AuthoringScope;
  rubric: Rubric;
  version: RubricVersion;
  readOnly: boolean;
  dashboardPreview?: RubricDashboardPreview;
  onPublished: () => void;
}) {
  const draft = useRubricDraft(scope, rubric.id, version);
  const trial = useTrialMark(scope, rubric.id);
  const action = useAction();
  const [tab, setTab] = useState<EditorTab>("structure");
  const [note, setNote] = useState<string | null>(null);

  const valid = draft.preview?.valid === true && !draft.checking;
  const promptMissing = draft.systemPrompt.trim() === "";
  const publishBlocked = readOnly
    ? null
    : draft.checking
      ? "Checking the latest edit…"
      : draft.problems.length > 0
        ? `Fix ${draft.problems.length} ${draft.problems.length === 1 ? "problem" : "problems"} to publish.`
        : promptMissing
          ? "Add marking instructions on the Marking tab to publish."
          : draft.dirty
            ? "Save your changes to publish."
            : null;

  const counts = useMemo(() => {
    const byTab: Record<BuilderTab, number> = { structure: 0, rating: 0, display: 0 };
    for (const problem of draft.problems) byTab[tabFor(problem)] += 1;
    return byTab;
  }, [draft.problems]);
  const withCount = (label: string, count: number) => (count > 0 ? `${label} · ${count}` : label);

  const pick = (problem: Problem) => {
    setTab(tabFor(problem));
    // Wait a frame so the tab's inputs exist before scrolling to one.
    window.requestAnimationFrame(() => revealPath(problem.path));
  };

  const publish = () =>
    action.run("publish", async () => {
      try {
        await publishRubricVersion(scope, rubric.id, version.version);
      } catch (cause) {
        if (cause instanceof PlatformError && cause.code === "invalid_rubric") {
          draft.setRefusedProblems(problemsFromDetails(cause.details));
        }
        throw cause;
      }
      onPublished();
    });

  const fillInstructions = () =>
    action.run("draft", async () => {
      const answer = await draftRubricInstructions(scope, draft.structure);
      const { structure, filled } = applyInstructionSuggestions(draft.structure, answer.items);
      draft.edit(() => structure);
      setNote(filled === 0 ? "Every place already has instructions." : `Drafted instructions for ${filled} ${filled === 1 ? "place" : "places"}. Read them before you save.`);
    });

  const runTrial = (body: TrialMarkRequest) =>
    void action.run("trial", async () => {
      // A trial marks the saved version, so unsaved edits are saved first.
      if (draft.dirty && !readOnly) await draft.save();
      await trial.start(version.version, body);
    });

  const editorTabs: { id: EditorTab; label: string }[] = [
    { id: "structure", label: withCount("Structure", counts.structure) },
    { id: "rating", label: withCount("Rating", counts.rating) },
    { id: "display", label: withCount("Results & dashboard", counts.display) },
    { id: "marking", label: "Marking" },
  ];

  return (
    <RubricBuilderProvider value={{ structure: draft.structure, edit: draft.edit, problems: draft.problems, readOnly }}>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-osce-lg border border-osce-border bg-osce-surface px-4 py-3">
          <p className="text-osce-meta text-osce-ink-500">
            {readOnly
              ? "This version is read-only. Start a new draft to change it."
              : draft.dirty
                ? "Unsaved changes."
                : "All changes saved."}
            {publishBlocked && !readOnly ? <span className="ml-2 text-osce-ink-400">{publishBlocked}</span> : null}
          </p>
          {readOnly ? null : (
            <div className="flex flex-wrap gap-2">
              <AuthoringButton variant="ghost" size="sm" isLoading={action.busy === "draft"} disabled={action.busy !== null || !valid} onClick={() => void fillInstructions()}>
                Draft instructions
              </AuthoringButton>
              <AuthoringButton variant="secondary" size="sm" isLoading={action.busy === "save"} disabled={action.busy !== null || !draft.dirty || promptMissing} onClick={() => void action.run("save", draft.save)}>
                Save draft
              </AuthoringButton>
              <AuthoringButton variant="commit" size="sm" isLoading={action.busy === "publish"} disabled={action.busy !== null || publishBlocked !== null} onClick={() => void publish()}>
                Publish
              </AuthoringButton>
            </div>
          )}
        </div>

        {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
        {note ? <Alert tone="info">{note}</Alert> : null}
        {draft.previewError ? <Alert tone="warning">The draft could not be checked: {draft.previewError.message}</Alert> : null}

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,460px)]">
          <div className="min-w-0 space-y-4">
            <B2CSegmentedTabs items={editorTabs} value={tab} onChange={setTab} compact aria-label="Rubric editor" />
            {tab === "structure" ? <SectionList /> : null}
            {tab === "rating" ? <RatingPanel /> : null}
            {tab === "display" ? <DisplayPanel /> : null}
            {tab === "marking" ? (
              <MarkingPanel
                systemPrompt={draft.systemPrompt}
                onSystemPrompt={draft.setSystemPrompt}
                pacing={draft.pacing}
                onPacing={draft.setPacing}
                markingLayout={draft.markingLayout}
                onMarkingLayout={draft.setMarkingLayout}
                title={rubric.title}
                readOnly={readOnly}
                layoutRequired={scope.kind === "platform"}
              />
            ) : null}
          </div>

          <aside className="min-w-0 space-y-4 xl:sticky xl:top-4">
            {readOnly ? null : <ProblemList problems={draft.problems} structure={draft.structure} checking={draft.checking} onPick={pick} />}
            <Panel title="Preview" description="What a candidate sees, from a made-up result.">
              <PreviewPane
                inputs={previewInputs(draft.preview, draft.structure)}
                dashboard={dashboardPreview}
                emptyMessage={draft.checking ? "Checking the draft…" : "Fix the problems to see the preview."}
              />
            </Panel>
            <Panel title="Trial mark" description="Mark a real conversation against this version. Nothing is saved.">
              <TrialPanel
                trial={trial}
                inputs={trialInputs(trial.snapshot, draft.preview, draft.structure)}
                blockedReason={valid ? null : "A trial needs a rubric with no problems."}
                onRun={runTrial}
              />
            </Panel>
          </aside>
        </div>
      </div>
    </RubricBuilderProvider>
  );
}
