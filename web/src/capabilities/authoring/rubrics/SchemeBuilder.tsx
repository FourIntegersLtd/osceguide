"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Panel, StepGuide } from "@/foundation/ui";
import { useLeaveGuard } from "@/foundation/hooks";
import { PlatformError } from "@/foundation/platform-client";
import { useSurface } from "@/capabilities";
import {
  addRubricVersion,
  archiveRubricVersion,
  draftRubricInstructions,
  publishRubricVersion,
  type AuthoringScope,
  type Rubric,
  type RubricVersion,
  type TrialMarkRequest,
} from "@/capabilities/authoring/api";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { AdvancedDisclosure } from "@/capabilities/authoring/rubrics/AdvancedDisclosure";
import type { RubricDashboardPreview } from "@/capabilities/authoring/rubrics/dashboardSlot";
import { FeedbackBlock } from "@/capabilities/authoring/rubrics/FeedbackBlock";
import { PassRuleBlock } from "@/capabilities/authoring/rubrics/PassRuleBlock";
import { PreviewPane } from "@/capabilities/authoring/rubrics/PreviewPane";
import { ProblemList, revealPath } from "@/capabilities/authoring/rubrics/ProblemList";
import { previewInputs, trialInputs } from "@/capabilities/authoring/rubrics/previewModel";
import { ScaleBlock } from "@/capabilities/authoring/rubrics/ScaleBlock";
import { SchemeDialogs } from "@/capabilities/authoring/rubrics/SchemeDialogs";
import { SchemeFooter } from "@/capabilities/authoring/rubrics/SchemeFooter";
import { SchemeNotices } from "@/capabilities/authoring/rubrics/SchemeNotices";
import { SchemeOutline, type RevealRequest } from "@/capabilities/authoring/rubrics/SchemeOutline";
import { SchemeTabBar } from "@/capabilities/authoring/rubrics/SchemeTabBar";
import { applySuggestions, problemsFromDetails, tabOfPath, cannotShow, type Problem, type SchemeTabId } from "@/capabilities/authoring/rubrics/schemeModel";
import { CONTENT_TABS, SCHEME_TABS, tabFooter } from "@/capabilities/authoring/rubrics/schemeTabs";
import { rubricNextAction, rubricSteps } from "@/capabilities/authoring/rubrics/rubricSteps";
import { TrialPanel } from "@/capabilities/authoring/rubrics/TrialPanel";
import { useSchemeDraft } from "@/capabilities/authoring/rubrics/useSchemeDraft";
import { useSchemeTab } from "@/capabilities/authoring/rubrics/useSchemeTab";
import { useTrialMark } from "@/capabilities/authoring/rubrics/useTrialMark";
import { olderPublished } from "@/capabilities/authoring/rubrics/versionRows";
import { VersionsTab } from "@/capabilities/authoring/rubrics/VersionsTab";
import { rubricEditPath } from "@/capabilities/authoring/templates/paths";

/** One marking scheme version, edited tab by tab (the tab is in the URL) with its preview and problems beside it. Publish is offered once it is saved and the backend finds nothing wrong. */
export function SchemeBuilder({
  scope,
  rubric,
  version,
  readOnly,
  owned,
  dashboardPreview,
  examHref,
  onPublished,
  onStale,
}: {
  scope: AuthoringScope;
  rubric: Rubric;
  version: RubricVersion;
  readOnly: boolean;
  /** This scope owns the scheme, so it may start drafts and archive versions. */
  owned: boolean;
  dashboardPreview?: RubricDashboardPreview;
  /** The New exam sheet that sent the author here; publishing then offers the way back. */
  examHref?: string | null;
  onPublished: () => void;
  /** Someone else saved this version first; reload it. */
  onStale: () => void;
}) {
  const [conflict, setConflict] = useState(false);
  const draft = useSchemeDraft(scope, rubric.id, version, () => setConflict(true));
  const trial = useTrialMark(scope, rubric.id);
  const action = useAction();
  const router = useRouter();
  const { tab, published, go, markPublished } = useSchemeTab();
  const { hrefFor } = useSurface();
  // JSON typed on the Advanced tab and not yet applied: it counts as an unsaved change.
  const [jsonText, setJsonText] = useState<string | null>(null);
  const jsonPending = jsonText !== null;
  const leave = useLeaveGuard((draft.dirty || jsonPending) && !readOnly);
  const [note, setNote] = useState<string | null>(null);
  const [confirmPublish, setConfirmPublish] = useState(false);
  const [archiving, setArchiving] = useState<RubricVersion | null>(null);
  const [openJson, setOpenJson] = useState(false);
  const [draftExists, setDraftExists] = useState(false);
  const [reveal, setReveal] = useState<RevealRequest | null>(null);

  const editJson = () => (setOpenJson(true), go("advanced"));

  const valid = draft.preview?.valid === true && !draft.checking;
  const promptMissing = draft.systemPrompt.trim() === "";
  const state = { status: version.status, dirty: draft.dirty, checking: draft.checking, problems: draft.problems.length, promptMissing };
  const next = rubricNextAction(state);
  const publishBlocked = readOnly || next.id === "publish" ? null : next.line;
  const versions = rubric.versions ?? [];
  const openDraft = versions.find((v) => v.status === "draft");
  const older = olderPublished(versions, version.version);

  // While the preview is being worked out, last time's problems are stale: show none rather than wrong ones.
  const problems: readonly Problem[] = draft.checking ? [] : draft.problems;
  const redCount = (id: SchemeTabId) => problems.filter((p) => tabOfPath(p.path) === id).length;
  const pick = (problem: Problem) => {
    go(tabOfPath(problem.path));
    // Outline rows are opened by the outline itself; the other tabs mount on the next render, then reveal.
    if (tabOfPath(problem.path) === "domains") setReveal({ path: problem.path, nonce: (reveal?.nonce ?? 0) + 1 });
    else window.requestAnimationFrame(() => window.requestAnimationFrame(() => revealPath(problem.path)));
  };

  const publish = () =>
    action.run("publish", async () => {
      try {
        await publishRubricVersion(scope, rubric.id, version.version);
      } catch (cause) {
        if (cause instanceof PlatformError && cause.code === "invalid_rubric") draft.setRefusedProblems(problemsFromDetails(cause.details));
        throw cause;
      }
      if (examHref) router.push(examHref);
      else {
        markPublished();
        onPublished();
      }
    });

  const fillInstructions = () =>
    action.run("draft", async () => {
      const answer = await draftRubricInstructions(scope, draft.structure as unknown as Record<string, unknown>);
      const filled = applySuggestions(draft.structure, answer.items).filled;
      draft.edit((current) => applySuggestions(current, answer.items).scheme);
      setNote(filled === 0 ? "Every place already has instructions." : `Drafted instructions for ${filled} ${filled === 1 ? "place" : "places"}. Read them before you save.`);
    });

  const runTrial = (body: TrialMarkRequest) =>
    jsonPending ? undefined : void action.run("trial", async () => {
      if (draft.dirty && !readOnly) await draft.save();
      await trial.start(version.version, body);
    });

  const startDraft = (from?: number) => {
    if (openDraft) return setDraftExists(true);
    void action.run("add", async () => {
      const created = await addRubricVersion(scope, rubric.id, from);
      router.push(rubricEditPath(hrefFor, rubric.id, created.version));
    });
  };

  const footer = tabFooter(tab);
  const scheme = draft.structure;
  const onScheme = (s: typeof scheme) => draft.edit(() => s);
  const seeFirstProblem = () => problems[0] && pick(problems[0]);
  // The last step's Next is Publish; with nothing to fix and nothing to publish yet it says why.
  const publishStuck = footer.next === null && !readOnly && publishBlocked !== null && problems.length === 0;
  const onNext = () => {
    if (footer.next) return go(footer.next);
    if (publishBlocked === null) return setConfirmPublish(true);
    seeFirstProblem();
  };

  return (
    <>
      <div className="space-y-4">
        <StepGuide steps={rubricSteps(state)} line={readOnly ? "This version is read-only. Start a new draft to change it." : next.line} working={next.id === "wait"}>
          {readOnly ? null : (
            <div className="flex flex-wrap gap-2">
              <AuthoringButton variant="secondary" size="sm" isLoading={action.busy === "publish"} disabled={action.busy !== null || publishBlocked !== null} onClick={() => setConfirmPublish(true)}>
                {examHref ? "Publish and go back" : "Publish"}
              </AuthoringButton>
              <AuthoringButton variant="commit" size="sm" isLoading={action.busy === "save"} disabled={action.busy !== null || !draft.dirty || promptMissing || jsonPending} onClick={() => action.run("save", draft.save)}>
                Save draft
              </AuthoringButton>
            </div>
          )}
        </StepGuide>

        <SchemeNotices
          conflict={conflict}
          onStale={onStale}
          error={action.error}
          note={note}
          checkError={draft.previewError?.message ?? null}
          readOnly={readOnly}
          owned={owned}
          version={version.version}
          status={version.status}
          exams={version.used_by_exams ?? []}
          starting={action.busy === "add"}
          onNewDraft={() => startDraft()}
          problemCount={problems.length}
          blocked={publishBlocked !== null}
          onSeeProblems={seeFirstProblem}
          published={published}
          older={older}
          onOpenExam={() => router.push(hrefFor("/authoring/exams"))}
          jsonPending={jsonPending}
          onOpenJson={editJson}
        />

        <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
          <div className="min-w-0 space-y-4">
            <SchemeTabBar tab={tab} redCount={redCount} onGo={go} />

            {cannotShow(scheme) && CONTENT_TABS.includes(tab) ? (
              <Panel title={SCHEME_TABS.find((t) => t.id === tab)?.label}>
                <Alert tone="info">
                  The builder cannot show this marking scheme, so this tab is empty. Edit it as JSON under Advanced.{" "}
                  <AuthoringButton variant="ghost" size="sm" onClick={editJson}>Open the JSON</AuthoringButton>
                </Alert>
              </Panel>
            ) : null}
            <div id="scheme-panel" role="tabpanel" aria-labelledby={`scheme-tab-${tab}`} className="min-w-0">
              {tab === "domains" ? <SchemeOutline scheme={scheme} onScheme={onScheme} readOnly={readOnly} problems={problems} reveal={reveal} onJump={go} onEditCustom={editJson} /> : null}
              {tab === "scale" && !cannotShow(scheme) ? <ScaleBlock scheme={scheme} onScheme={onScheme} readOnly={readOnly} problems={problems} /> : null}
              {tab === "pass" && !cannotShow(scheme) ? <PassRuleBlock scheme={scheme} onScheme={onScheme} readOnly={readOnly} problems={problems} /> : null}
              {tab === "feedback" && !cannotShow(scheme) ? <FeedbackBlock scheme={scheme} onScheme={onScheme} readOnly={readOnly} problems={problems} onEditCustom={editJson} /> : null}
              {tab === "advanced" ? (
                <AdvancedDisclosure
                  scheme={scheme}
                  onScheme={onScheme}
                  systemPrompt={draft.systemPrompt}
                  onSystemPrompt={draft.setSystemPrompt}
                  pacing={draft.pacing}
                  onPacing={draft.setPacing}
                  markingLayout={draft.markingLayout}
                  onMarkingLayout={draft.setMarkingLayout}
                  readOnly={readOnly}
                  layoutRequired={scope.kind === "platform"}
                  draft={{ run: () => void fillInstructions(), busy: action.busy === "draft", allowed: valid && action.busy === null }}
                  openJson={openJson || cannotShow(scheme)}
                  json={{ text: jsonText, onText: setJsonText }}
                />
              ) : null}
              {tab === "trial" ? (
                <Panel title="Trial mark" description="Mark a real attempt or a pasted transcript with this draft, before anyone else does.">
                  <TrialPanel trial={trial} inputs={trialInputs(trial.snapshot, draft.preview)} blockedReason={jsonPending ? "Apply or discard the JSON edits on the Advanced tab first." : valid ? null : "A trial needs a marking scheme with no problems."} onRun={runTrial} />
                </Panel>
              ) : null}
              {tab === "versions" ? (
                <VersionsTab
                  versions={versions}
                  current={rubric.current_version_id}
                  open={version.version}
                  owned={owned}
                  adding={action.busy === "add"}
                  onOpen={(n) => leave.leaveTo(rubricEditPath(hrefFor, rubric.id, n))}
                  onArchive={setArchiving}
                  onNewDraft={() => startDraft()}
                  onDraftFrom={startDraft}
                />
              ) : null}
            </div>

            <SchemeFooter footer={footer} readOnly={readOnly} stuck={publishStuck ? publishBlocked : null} onBack={() => footer.back && go(footer.back)} onNext={onNext} />
          </div>

          <aside className="min-w-0 space-y-4 xl:sticky xl:top-4">
            <Panel title="Preview: candidate feedback" description="What a candidate sees, from a made-up result.">
              <PreviewPane inputs={previewInputs(draft.preview)} dashboard={dashboardPreview} emptyMessage={draft.checking ? "Checking the draft…" : "Fix the problems to see the preview."} />
            </Panel>
            <Panel title="Problems">
              {readOnly ? <p className="text-osce-meta text-ink-muted">Read-only.</p> : <ProblemList problems={draft.problems} scheme={scheme} checking={draft.checking} onPick={pick} />}
            </Panel>
          </aside>
        </div>
      </div>
      <SchemeDialogs
        version={version}
        older={older}
        publishing={confirmPublish}
        onPublishCancel={() => setConfirmPublish(false)}
        onPublish={() => {
          setConfirmPublish(false);
          void publish();
        }}
        archiving={archiving}
        onArchiveCancel={() => setArchiving(null)}
        onArchive={(target) => {
          setArchiving(null);
          void action.run("archive", async () => {
            await archiveRubricVersion(scope, rubric.id, target.version);
            onPublished();
          });
        }}
        draftExists={draftExists}
        openDraftVersion={openDraft?.version}
        onDraftExistsClose={() => setDraftExists(false)}
        leaving={leave.asking}
        onStay={leave.stay}
        onLeave={() => {
          const href = leave.confirmLeave();
          if (href) router.push(href);
        }}
      />
    </>
  );
}
