"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Alert, Badge, Panel, StepGuide } from "@/foundation/ui";
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
import { versionRows } from "@/capabilities/authoring/rubrics/versionRows";
import { LeaveConfirmModal } from "@/foundation/ui";
import { useLeaveGuard } from "@/foundation/hooks";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { RubricBuilderProvider } from "@/capabilities/authoring/rubrics/builderContext";
import type { RubricDashboardPreview } from "@/capabilities/authoring/rubrics/dashboardSlot";
import { DisplayPanel } from "@/capabilities/authoring/rubrics/DisplayPanel";
import { applyInstructionSuggestions } from "@/capabilities/authoring/rubrics/draftInstructions";
import { MarkingPanel } from "@/capabilities/authoring/rubrics/MarkingPanel";
import { PreviewPane } from "@/capabilities/authoring/rubrics/PreviewPane";
import { ProblemList, revealPath } from "@/capabilities/authoring/rubrics/ProblemList";
import { problemsFromDetails, type Problem } from "@/capabilities/authoring/rubrics/problems";
import { previewInputs, trialInputs } from "@/capabilities/authoring/rubrics/previewModel";
import { rubricNextAction, rubricSteps } from "@/capabilities/authoring/rubrics/rubricSteps";
import { RatingPanel } from "@/capabilities/authoring/rubrics/RatingPanel";
import { SectionList } from "@/capabilities/authoring/rubrics/SectionEditor";
import { TrialPanel } from "@/capabilities/authoring/rubrics/TrialPanel";
import { useRubricDraft } from "@/capabilities/authoring/rubrics/useRubricDraft";
import { useTrialMark } from "@/capabilities/authoring/rubrics/useTrialMark";

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
  examHref,
  onPublished,
  onStale,
}: {
  scope: AuthoringScope;
  rubric: Rubric;
  version: RubricVersion;
  readOnly: boolean;
  dashboardPreview?: RubricDashboardPreview;
  /** The New exam sheet that sent the author here; publishing then offers the way back. */
  examHref?: string | null;
  onPublished: () => void;
  /** Someone else saved this version first; reload it. */
  onStale: () => void;
}) {
  const draft = useRubricDraft(scope, rubric.id, version, onStale);
  const trial = useTrialMark(scope, rubric.id);
  const action = useAction();
  const router = useRouter();
  // Unsaved edits: the tab warning, and any link inside the app asks first.
  const leave = useLeaveGuard(draft.dirty && !readOnly);
  const [note, setNote] = useState<string | null>(null);

  const valid = draft.preview?.valid === true && !draft.checking;
  const promptMissing = draft.systemPrompt.trim() === "";
  const state = {
    status: version.status,
    dirty: draft.dirty,
    checking: draft.checking,
    problems: draft.problems.length,
    promptMissing,
  };
  const next = rubricNextAction(state);
  const publishBlocked = readOnly || next.id === "publish" ? null : next.line;

  // A problem lives on one page now: scroll to its input.
  const pick = (problem: Problem) => revealPath(problem.path);

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
      // Opened from the New exam sheet: publishing is the last step, so go back to it.
      if (examHref) router.push(examHref);
      else onPublished();
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

  return (
    <RubricBuilderProvider value={{ structure: draft.structure, edit: draft.edit, problems: draft.problems, readOnly }}>
      <div className="space-y-4">
        <StepGuide steps={rubricSteps(state)} line={readOnly ? "This version is read-only. Start a new draft to change it." : next.line} working={next.id === "wait"}>
          {readOnly ? null : (
            <div className="flex flex-wrap gap-2">
              <AuthoringButton variant="secondary" size="sm" isLoading={action.busy === "save"} disabled={action.busy !== null || !draft.dirty || promptMissing} onClick={() => action.run("save", draft.save)}>
                Save draft
              </AuthoringButton>
              <AuthoringButton variant="commit" size="sm" isLoading={action.busy === "publish"} disabled={action.busy !== null || publishBlocked !== null} onClick={() => publish()}>
                {examHref ? "Publish and go back" : "Publish"}
              </AuthoringButton>
            </div>
          )}
        </StepGuide>

        {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
        {note ? <Alert tone="info">{note}</Alert> : null}
        {draft.previewError ? <Alert tone="warning">The draft could not be checked: {draft.previewError.message}</Alert> : null}

        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,460px)]">
          <div className="min-w-0 space-y-4">
            <BoardSection title="Areas marked" note="Each domain is rated on its own">
              <SectionList />
            </BoardSection>
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
              draft={{ run: () => void fillInstructions(), busy: action.busy === "draft", allowed: valid && action.busy === null }}
            />
            <RatingPanel />
            <DisplayPanel />
          </div>

          <aside className="min-w-0 space-y-4 xl:sticky xl:top-4">
            <Panel title="Preview: candidate feedback" description="What a candidate sees, from a made-up result.">
              <PreviewPane
                inputs={previewInputs(draft.preview, draft.structure)}
                dashboard={dashboardPreview}
                emptyMessage={draft.checking ? "Checking the draft…" : "Fix the problems to see the preview."}
              />
            </Panel>
            <Panel title="Problems">
              {readOnly ? <p className="text-osce-meta text-ink-muted">Read-only.</p> : <ProblemList problems={draft.problems} structure={draft.structure} checking={draft.checking} onPick={pick} />}
            </Panel>
            {/* Read-only on purpose: publishing and archiving a version live on the versions page. */}
            <Panel title="Versions">
              <ul className="space-y-1.5">
                {versionRows(rubric.versions ?? []).map((row) => (
                  <li key={row.id} className="flex items-center justify-between gap-2 text-osce-body text-ink">
                    <span>
                      <span className="font-medium">v{row.version}</span>{" "}
                      <span className="text-osce-caption text-ink-muted">{row.detail}</span>
                    </span>
                    <Badge tone={row.chip.tone} size="sm" dot>
                      {row.chip.label}
                    </Badge>
                  </li>
                ))}
              </ul>
            </Panel>
            <Panel title="Trial mark" description="Mark a real attempt or a pasted transcript with this draft, before anyone else does.">
              <TrialPanel
                trial={trial}
                inputs={trialInputs(trial.snapshot, draft.preview, draft.structure)}
                blockedReason={valid ? null : "A trial needs a marking scheme with no problems."}
                onRun={runTrial}
              />
            </Panel>
          </aside>
        </div>
      </div>
      <LeaveConfirmModal
        isOpen={leave.asking}
        onStay={leave.stay}
        onLeave={() => {
          const href = leave.confirmLeave();
          if (href) router.push(href);
        }}
      />
    </RubricBuilderProvider>
  );
}

function BoardSection({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <div>
        <h2 className="text-osce-body font-semibold text-ink">{title}</h2>
        {note ? <p className="text-osce-caption text-ink-muted">{note}</p> : null}
      </div>
      {children}
    </section>
  );
}
