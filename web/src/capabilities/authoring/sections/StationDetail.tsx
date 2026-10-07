"use client";

import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  HiOutlineArchiveBox,
  HiOutlineArrowLeft,
  HiOutlineDocumentDuplicate,
  HiOutlineTrash,
} from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  Button,
  ConfirmModal,
  Input,
  LeaveConfirmModal,
  Panel,
  StepGuide,
} from "@/foundation/ui";
import { useLeaveGuard } from "@/foundation/hooks";
import { StationInstanceContentPanel } from "@/capabilities/authoring/sections/StationInstanceContentPanel";
import { validateStationContentScoped } from "@/capabilities/authoring/lib/b2cStationContentScope";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { StationVersionHistory } from "@/capabilities/authoring/sections/StationVersionHistory";
import { StationUsedBy } from "@/capabilities/authoring/sections/StationUsedBy";
import {
  AuthoringIconAction,
  AuthoringRowActions,
} from "@/capabilities/authoring/parts/AuthoringIconAction";
import {
  addStationVersion,
  checkStationFacts,
  archiveStationVersion,
  deleteStationVersion,
  editStationVersion,
  produceStation,
  publishStationVersion,
  removeStationPhoto,
  stopProducingStation,
  supportsBrief,
  supportsFactCheck,
  uploadStationPhotos,
  type Station,
  type StationTemplate,
  type StationVersion,
} from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { renamedTitle } from "@/capabilities/authoring/parts/stationTitle";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import {
  ERROR_STEPS,
  FactCheck,
  ProduceForm,
  RunLog,
  briefOf,
  corrected,
  reopened,
  ruled,
  runOf,
  uncorrected,
  type Facts,
} from "@/capabilities/fact-check";
import {
  stationNext,
  stationSteps,
  useStationReview,
  type StationStepId,
} from "@/capabilities/authoring/parts/stationPipeline";
import { listStationVersions } from "@/capabilities/stations";
import { BriefEditor } from "@/capabilities/authoring/sections/BriefEditor";
import Link from "next/link";
import { useSurface } from "@/capabilities";
import { stationTemplateNewPath } from "@/capabilities/authoring/templates/paths";
import { legacyB2cStationStructure } from "@/capabilities/authoring/lib/legacyB2cStationStructure";

function structureForTemplateVersion(
  templates: StationTemplate[],
  templateVersionId: string | null | undefined,
): StationStructure | null {
  if (!templateVersionId) return null;
  for (const template of templates) {
    const version = template.versions.find((v) => v.id === templateVersionId);
    if (version) {
      return version.structure as StationStructure;
    }
  }
  return null;
}

/**
 * One station's working version, as steps: draft it, check its facts (the
 * catalogue only), publish it. One bar holds the screen's next action, Save
 * included, so an edit or a fact-check ruling is never left without a way to store it.
 */
export function StationDetail({
  station,
  templates,
  onBack,
}: {
  station: Station;
  templates: StationTemplate[];
  onBack: () => void;
}) {
  const scope = useAuthoringScope();
  const router = useRouter();
  const { hrefFor } = useSurface();
  const [working, setWorking] = useState<StationVersion | null>(null);
  const [editContent, setEditContent] = useState<Record<string, unknown>>({});
  /** Fact-check rulings made since the last save; they are saved with the content. */
  const [ruledFacts, setRuledFacts] = useState<Facts | null>(null);
  const action = useAction();
  const canAuthor = useCanAuthor();
  /** The station's name as last saved, and as typed; a draft saves a rename with its content. */
  const [savedTitle, setSavedTitle] = useState(station.title);
  const [title, setTitle] = useState(station.title);
  const renamed = renamedTitle(title, savedTitle);
  const [confirming, setConfirming] = useState<"archive" | "delete" | null>(null);
  /** The step on screen; null until the review has loaded and says where to open. */
  const [step, setStep] = useState<StationStepId | null>(null);
  /** A fresh draft opens on the Draft step: it starts as a copy, so the reader edits it first. */
  const openOnDraft = useRef(false);
  const [askingBack, setAskingBack] = useState(false);

  const version = working?.version ?? station.version;
  const status = working?.status ?? station.status;
  const isDraft = status !== "published" && status !== "archived";
  /** A reader sees the draft but changes none of it. */
  const editable = isDraft && canAuthor;
  const templateVersionId = station.template_version_id ?? null;

  const structure = useMemo(() => {
    const fromTemplate = structureForTemplateVersion(templates, templateVersionId);
    if (fromTemplate) return fromTemplate;
    const src = (working?.content ?? station.content ?? {}) as Record<string, unknown>;
    return legacyB2cStationStructure(station.exam_code, src);
  }, [templates, templateVersionId, station.exam_code, station.content, working?.content]);

  useEffect(() => {
    const src = (working?.content ?? station.content ?? {}) as Record<string, unknown>;
    setEditContent({ ...src });
    setRuledFacts(null);
    setStep(openOnDraft.current ? "draft" : null);
    openOnDraft.current = false;
  }, [station.id, version]);

  /*
    Media is editable on a published version for the same reason the reading
    brief is: it is what a candidate is shown rather than what they are marked
    against, and an attempt freezes its own copy of the scenario. An archived
    version still refuses. The server writes the block, so its content wins.
  */
  const media =
    status === "archived"
      ? undefined
      : {
          upload: async (blockId: string, files: File[]) => {
            const result = await uploadStationPhotos(scope, station.id, version, blockId, files);
            setEditContent((result.version.content ?? {}) as Record<string, unknown>);
            return { uploaded: result.uploaded, failed: result.failed };
          },
          remove: async (url: string) => {
            const updated = await removeStationPhoto(scope, station.id, version, url);
            setEditContent((updated.content ?? {}) as Record<string, unknown>);
          },
        };

  /** Puts what the agent saved on screen, dropping nothing: it only ran while there were no edits. */
  const reloadProduced = useCallback(() => {
    void listStationVersions(station.id).then((versions) => {
      const produced = versions.find((entry) => entry.version === version);
      if (!produced) return;
      setWorking(produced);
      setEditContent({ ...((produced.content ?? {}) as Record<string, unknown>) });
      setRuledFacts(null);
    });
  }, [station.id, version]);

  const factCheck = supportsFactCheck(scope) && status !== "archived";
  const reviewState = useStationReview(scope, station.id, version, factCheck, reloadProduced);
  const { facts, checking, producing } = reviewState;
  const review = reviewState.review;

  const contentChanged =
    JSON.stringify(editContent) !== JSON.stringify(working?.content ?? station.content ?? {});
  const validation = structure ? validateStationContentScoped(structure, editContent) : null;
  const contentValid = validation ? validation.ok : Object.keys(editContent).length > 0;
  const unsaved = ruledFacts !== null || contentChanged || renamed !== undefined;
  const leaveGuard = useLeaveGuard(unsaved);
  // A rename alone saves even while the content is still incomplete.
  const saveBlocker = !title.trim()
    ? "Give the station a name."
    : !contentValid && (contentChanged || !renamed)
      ? ((validation && !validation.ok ? validation.errors[0] : undefined) ??
        "Fill all required fields.")
      : null;

  const steps = stationSteps(editContent, facts, { factCheck, status });
  const next = stationNext(editContent, facts, {
    factCheck,
    status,
    producing,
    checking,
    unsaved,
    saveBlocker,
  });
  // Open on the step the next action belongs to once the review is in, then stay where the
  // reader goes: a ruling makes the edits unsaved, and that must not move them off the claims.
  if (step === null && !reviewState.loading) setStep(next.step);
  const current = step ?? next.step;
  const busy = checking || producing;
  const locked = unsaved || busy || action.busy !== null;

  const save = () =>
    void action.run("save", async () => {
      if (saveBlocker) throw new Error(saveBlocker);
      setWorking(
        await editStationVersion(scope, station.id, version, editContent, {
          facts: ruledFacts ?? undefined,
          title: renamed,
        }),
      );
      if (renamed) setSavedTitle(renamed);
      setRuledFacts(null);
    });

  const newDraft = () =>
    void action.run("add", async () => {
      const added = await addStationVersion(scope, station.id);
      openOnDraft.current = true;
      setWorking(added);
    });

  const publish = () =>
    void action.run("publish", async () => {
      if (validation && !validation.ok) {
        throw new Error(validation.errors[0] ?? "Please fill all required fields.");
      }
      setWorking(await publishStationVersion(scope, station.id, version));
    });

  const checkFacts = () =>
    void action.run("check", async () => {
      await checkStationFacts(scope, station.id, version);
      reviewState.setChecking(true);
      setStep("facts");
    });

  const produce = (brief: string) =>
    void action.run("produce", async () => {
      await produceStation(scope, station.id, version, { brief });
      reviewState.setProducing(true);
      reviewState.reload();
    });

  function rule(nextFacts: Facts) {
    reviewState.setFacts(nextFacts);
    setRuledFacts(nextFacts);
  }

  const nextButton = () => {
    if (!canAuthor) return null;
    const run = (label: string, key: string, onClick: () => void, disabled = locked) => (
      <Button size="sm" disabled={disabled} isLoading={action.busy === key} onClick={onClick}>
        {label}
      </Button>
    );
    switch (next.id) {
      case "save":
        return run("Save", "save", save, saveBlocker !== null || action.busy !== null);
      case "check-facts":
        return run("Check facts", "check", checkFacts);
      case "rule":
        return current === "facts" ? null : run("Review claims", "", () => setStep("facts"));
      case "publish":
        return run("Publish", "publish", publish);
      case "new-version":
        return run(
          "New draft version",
          "add",
          newDraft,
          action.busy !== null,
        );
      default:
        return null;
    }
  };

  const drafted = steps[0]?.state === "done";
  const produceForm = (
    <ProduceForm
      key={briefOf(review?.brief)?.brief ?? ""}
      brief={briefOf(review?.brief)}
      hint="With nothing written the agent drafts it, then checks the facts and corrects what the sources contradict."
      locked={locked}
      working={producing}
      primary={next.id === "produce"}
      onProduce={produce}
    />
  );
  const run = review ? runOf(review.run) : null;

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={unsaved ? () => setAskingBack(true) : onBack}
        className="inline-flex items-center gap-1.5 text-osce-body font-medium text-accent hover:underline"
      >
        <HiOutlineArrowLeft className="h-4 w-4 shrink-0" aria-hidden />
        Stations
      </button>

      <Panel padding="md">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {editable ? (
              <Input
                aria-label="Station name"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                className="font-semibold"
              />
            ) : (
              <h2 className="text-osce-body font-semibold text-ink">{savedTitle}</h2>
            )}
            <p className="mt-0.5 text-osce-caption text-ink-muted">
              {station.exam_code} · version {version}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={status} />
            {canAuthor ? (
            <AuthoringRowActions>
              {/* A draft is the version being worked on: a second draft is not offered. */}
              {isDraft ? null : (
              <AuthoringIconAction
                label={status === "archived" ? "New draft from this" : "New draft version"}
                busy={action.busy === "add"}
                busyLabel="Creating…"
                disabled={action.busy !== null}
                onClick={newDraft}
              >
                <HiOutlineDocumentDuplicate className="h-4 w-4" aria-hidden />
              </AuthoringIconAction>
              )}
              {status === "published" ? (
                <AuthoringIconAction
                  variant="warning"
                  label="Archive"
                  busy={action.busy === "archive"}
                  busyLabel="Archiving…"
                  disabled={action.busy !== null}
                  onClick={() => setConfirming("archive")}
                >
                  <HiOutlineArchiveBox className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
              {isDraft ? (
                <AuthoringIconAction
                  variant="danger"
                  label="Delete draft"
                  busy={action.busy === "delete"}
                  busyLabel="Deleting…"
                  disabled={action.busy !== null}
                  onClick={() => setConfirming("delete")}
                >
                  <HiOutlineTrash className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              ) : null}
            </AuthoringRowActions>
            ) : null}
          </div>
        </div>

        {!structure && templateVersionId ? (
          <p className="mt-3 text-osce-caption text-ink-muted">
            Template structure is not available in the catalogue. Reload templates or edit from the template list.
          </p>
        ) : null}
        {!structure && !templateVersionId ? (
          <p className="mt-3 text-osce-caption text-ink-muted">
            No layout is defined for exam {station.exam_code}. Create a station template for this exam
            first.{" "}
            <Link href={stationTemplateNewPath(hrefFor)} className="font-semibold text-accent underline">
              Create a station template
            </Link>
          </p>
        ) : null}
      </Panel>

      <LeaveConfirmModal
        isOpen={askingBack || leaveGuard.asking}
        onStay={() => {
          setAskingBack(false);
          leaveGuard.stay();
        }}
        onLeave={() => {
          const href = leaveGuard.confirmLeave();
          setAskingBack(false);
          if (href) router.push(href);
          else onBack();
        }}
      />

      <ConfirmModal
        isOpen={confirming !== null}
        onCancel={() => {
          if (action.busy) return;
          action.clearError();
          setConfirming(null);
        }}
        error={confirming !== null ? action.error : null}
        onConfirm={() => {
          const which = confirming;
          void action
            .run(which ?? "archive", async () => {
              if (which === "delete") {
                await deleteStationVersion(scope, station.id, version);
                onBack();
              } else {
                setWorking(await archiveStationVersion(scope, station.id, version));
              }
            })
            .then((ok) => {
              if (ok) setConfirming(null);
            });
        }}
        isLoading={confirming !== null && action.busy === confirming}
        title={
          confirming === "delete"
            ? `Delete draft v${version} of "${savedTitle}"?`
            : `Archive v${version} of "${savedTitle}"?`
        }
        confirmText={confirming === "delete" ? "Delete" : "Archive"}
        message={
          <>
            {confirming !== null ? <StationUsedBy stationId={station.id} version={version} /> : null}
            <span className="mt-1 block">
              {confirming === "delete"
                ? "The draft is removed. Published versions are untouched."
                : "Past attempts stay intact. The station is removed from the live library."}
            </span>
          </>
        }
      />

      <StepGuide steps={steps} current={current} onSelect={setStep} line={next.line} working={next.id === "wait"}>
        {nextButton()}
      </StepGuide>
      {action.error && confirming === null ? <Alert tone="danger">{action.error}</Alert> : null}
      {review?.error && !busy ? (
        <Alert tone="danger">
          The last {ERROR_STEPS[String(review.error.step)] ?? "fact check"} failed:{" "}
          {String(review.error.message ?? "")}
        </Alert>
      ) : null}
      {run ? (
        <RunLog
          run={run}
          running={producing}
          stopping={action.busy === "stop"}
          onStop={() =>
            void action.run("stop", async () => {
              await stopProducingStation(scope, station.id, version);
              reviewState.reload();
            })
          }
        />
      ) : null}

      {current === "draft" ? (
        // Remounted once a draft exists, so its panels open and fold the right way round.
        <div key={String(drafted)} className="space-y-4">
          {factCheck && editable && !drafted ? (
            <Panel title="What should it cover?" padding="sm">
              {produceForm}
            </Panel>
          ) : null}
          {structure ? (
            <Panel title="Station content" defaultOpen={drafted || !factCheck}>
              <p className="mb-4 text-osce-caption text-ink-muted">
                Version {version}.
                {editable
                  ? " Edit the sections below; Save in the bar above stores them."
                  : " Published, so it is read only. Create a new draft version to edit."}
              </p>
              <LegacyStationMeta content={editContent} stationTitle={savedTitle} />
              <StationInstanceContentPanel
                structure={structure}
                content={editContent}
                onChange={setEditContent}
                readOnly={!editable}
                media={media}
              />
            </Panel>
          ) : null}
          {supportsBrief(scope) && canAuthor ? (
            <BriefEditor
              key={`${station.id}:${version}`}
              stationId={station.id}
              version={version}
              initial={readBrief(working?.content ?? station.content)}
              onSaved={setWorking}
            />
          ) : null}
          {factCheck && editable && drafted ? (
            <Panel title="Produce again from a brief" padding="sm" defaultOpen={false}>
              {produceForm}
            </Panel>
          ) : null}
        </div>
      ) : null}

      {current === "facts" ? (
        <Panel title="Check the facts">
          <AsyncBoundary state={reviewState.load}>
            {() => (
              <FactCheck
                facts={facts}
                locked={locked}
                working={checking}
                onCheck={checkFacts}
                rulings={
                  // A ruling made while the agent produces would be overwritten when it finishes.
                  editable && facts && !busy
                    ? {
                        onAccept: (claim, swap) => {
                          if (swap) setEditContent(corrected(editContent, claim, swap));
                          rule(ruled(facts, claim.id, "accepted", swap ?? undefined));
                        },
                        onDismiss: (claim) => rule(ruled(facts, claim.id, "dismissed")),
                        onReopen: (claim) => {
                          setEditContent(uncorrected(editContent, claim));
                          rule(reopened(facts, claim.id));
                        },
                      }
                    : undefined
                }
              />
            )}
          </AsyncBoundary>
        </Panel>
      ) : null}

      {current === "publish" ? (
        <Panel title="Publish">
          <div className="flex flex-col gap-3 text-osce-body text-ink-muted">
            <p>
              Publishing makes v{version} the version candidates are assessed against. A published
              version is what an attempt was marked against, so it is archived rather than deleted.
            </p>
            {isDraft && !readBrief(working?.content ?? station.content).trim() ? (
              <Alert tone="warning">
                This station has no candidate brief, so candidates see nothing during reading time.
                You can still publish.
              </Alert>
            ) : null}
            {steps
              .filter((entry) => entry.id !== "publish" && entry.state !== "done")
              .map((entry) => (
                <Alert key={entry.id} tone="warning">
                  {entry.label}: {entry.note}.
                </Alert>
              ))}
            {/* Ready, the bar holds Publish; before then it stays possible from here. */}
            {canAuthor && isDraft && next.id !== "publish" ? (
              <Button
                size="sm"
                variant="secondary"
                className="w-fit"
                disabled={locked}
                isLoading={action.busy === "publish"}
                onClick={publish}
              >
                Publish anyway
              </Button>
            ) : null}
          </div>
        </Panel>
      ) : null}

      <StationVersionHistory stationId={station.id} />
    </div>
  );
}

function readBrief(content: unknown): string {
  if (!content || typeof content !== "object") return "";
  const { reading_brief: reading, candidate_brief: candidate } = content as Record<string, unknown>;
  const brief = typeof reading === "string" && reading.trim() ? reading : candidate;
  return typeof brief === "string" ? brief : "";
}

function LegacyStationMeta({
  content,
  stationTitle,
}: {
  content: Record<string, unknown>;
  stationTitle: string;
}) {
  const legacyId = typeof content.station_id === "string" ? content.station_id : "";
  const name =
    typeof content.station_name === "string" && content.station_name.trim()
      ? content.station_name
      : stationTitle;
  if (!legacyId && !name) return null;
  return (
    <div className="mb-6 grid grid-cols-1 gap-4 rounded-osce-lg border border-border bg-surface-raised/40 p-4 md:grid-cols-2">
      {legacyId ? (
        <div>
          <p className="text-osce-caption font-medium text-ink-muted">Station ID</p>
          <p className="mt-1 font-mono text-osce-body text-ink">{legacyId}</p>
        </div>
      ) : null}
      <div>
        <p className="text-osce-caption font-medium text-ink-muted">Station name</p>
        <p className="mt-1 text-osce-body text-ink">{name}</p>
      </div>
    </div>
  );
}
