"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  HiOutlineArrowDownTray,
  HiOutlineArrowLeft,
  HiOutlineCodeBracket,
  HiOutlineEye,
  HiOutlineLockOpen,
  HiOutlineTrash,
} from "react-icons/hi2";
import {
  Alert,
  Badge,
  Button,
  ConfirmModal,
  Input,
  Panel,
  StepGuide,
  Textarea,
} from "@/foundation/ui";
import { AuthoringIconAction } from "@/capabilities/authoring/parts/AuthoringIconAction";
import { AuthoringExamField } from "@/capabilities/authoring/parts/AuthoringExamField";
import {
  errorMessage,
  useAsync,
  useMeEvents,
  useToast,
} from "@/foundation/hooks";
import { MEDIA_KIND_LABELS, isMediaKind, type MediaKind } from "@/capabilities/media/api";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import {
  avStatus,
  isAvRunning,
  mergeContent,
} from "@/capabilities/staff-media/content/b2cMediaShapes";
import { BlogContentForm } from "@/capabilities/staff-media/forms/BlogContentForm";
import { B2cSlideDeckForm } from "@/capabilities/staff-media/forms/B2cSlideDeckForm";
import { PodcastContentForm } from "@/capabilities/staff-media/forms/PodcastContentForm";
import { SummaryContentForm } from "@/capabilities/staff-media/forms/SummaryContentForm";
import {
  acceptSuggestion,
  dismissSuggestion,
  reopenSuggestion,
  isSpokenKind,
  reviewOf,
} from "@/capabilities/staff-media/content/review";
import {
  nextAction,
  reviewSteps,
  type StepId,
} from "@/capabilities/staff-media/content/steps";
import { ERROR_STEPS, ProduceForm, RunLog } from "@/capabilities/fact-check";
import { HandCheckModal } from "@/capabilities/staff-media/parts/HandCheckModal";
import { ContentJsonEditor } from "@/capabilities/staff-media/parts/ContentJsonEditor";
import { FactCheck } from "@/capabilities/fact-check";
import {
  PublishStep,
  ScriptStep,
  VoiceStep,
} from "@/capabilities/staff-media/parts/ReviewSteps";
import {
  checkMediaFacts,
  deleteMedia,
  generateBlog,
  generatePodcastAudio,
  generatedTitle,
  generateSummaryPodcast,
  produceMedia,
  publishMedia,
  readMediaById,
  recordHandCheck,
  regenerateSlideAv,
  stopProduce,
  unlockMedia,
  unpublishMedia,
  updateMedia,
  writeMediaScript,
  type MediaItem,
} from "@/capabilities/staff-media/api";
import { learnerMediaPreviewPath } from "@/capabilities/staff-media/paths";

function contentRecord(item: MediaItem | null): Record<string, unknown> {
  if (
    !item?.content ||
    typeof item.content !== "object" ||
    Array.isArray(item.content)
  )
    return {};
  return item.content as Record<string, unknown>;
}

export function MediaDetailScreen({
  itemId,
  onBack,
}: {
  itemId: string;
  /** Back to the list, on the item's own tab once it is known. */
  onBack: (kind?: MediaKind) => void;
}) {
  const load = useAsync((signal) => readMediaById(itemId, signal), [itemId]);
  const action = useAction(load.reload);
  const toast = useToast();

  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [examCode, setExamCode] = useState("");
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [prompt, setPrompt] = useState("");
  const [jsonOpen, setJsonOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirm, setConfirm] = useState<"publish" | "save-publish" | "unpublish" | "unlock" | "hand-check" | null>(null);
  const [pollAv, setPollAv] = useState(false);
  const [step, setStep] = useState<StepId | null>(null);

  useEffect(() => {
    if (!load.data) return;
    setTitle(load.data.title);
    setSummary(load.data.summary ?? "");
    setExamCode(load.data.exam_code ?? "");
    setContent(contentRecord(load.data));
    const status = avStatus(contentRecord(load.data));
    setPollAv(isAvRunning(status));
    // Open on the step the next action belongs to, and stay where the reader then goes.
    const opened = nextAction(load.data.kind, contentRecord(load.data), {
      published: load.data.status === "published",
      unsaved: false,
    }).step;
    setStep((current) => current ?? opened);
  }, [load.data]);

  // The AV job publishes `media.updated` to the staff member who requested it
  // once it settles, so this re-reads on that event rather than on a timer.
  const reload = load.reload;
  useMeEvents(
    pollAv ? ["media.updated"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.media_id === itemId) reload();
      },
      [itemId, reload],
    ),
  );

  useEffect(() => {
    const status = avStatus(content);
    if (!isAvRunning(status)) setPollAv(false);
  }, [content]);

  const kind = load.data?.kind ?? "summary";
  const kindLabel = isMediaKind(kind) ? MEDIA_KIND_LABELS[kind].one : "Item";
  const backToList = () => onBack(isMediaKind(kind) ? kind : undefined);

  const previewHref = useMemo(
    () => (load.data ? learnerMediaPreviewPath(load.data) : null),
    [load.data],
  );

  const save = (andPublish = false) =>
    action.run(andPublish ? "save-publish" : "save", async () => {
      const saved = await updateMedia(itemId, {
        title: title.trim(),
        summary: summary.trim() || null,
        content,
        exam_code: examCode.trim(),
      });
      if (andPublish) {
        await publishMedia(itemId);
        toast.success("Saved and published");
      } else if (isAvRunning(avStatus(contentRecord(saved)))) {
        // The draft moved under a checked script, so the server is rewriting the lines it touched.
        toast.success("Saved", "The script is being brought up to date and checked again.");
      } else {
        toast.success("Saved");
      }
      load.reload();
    });

  // A check or a voicing reads what is stored, so the panel holds its buttons
  // back while the form is ahead of the server. The details count too, or a
  // deck's exam or title edit would have no Save to reach the server.
  const unsaved = useMemo(
    () =>
      !!load.data &&
      (title !== load.data.title ||
        summary !== (load.data.summary ?? "") ||
        examCode.trim().toLowerCase() !== (load.data.exam_code ?? "").toLowerCase() ||
        JSON.stringify(content) !== JSON.stringify(contentRecord(load.data))),
    [title, summary, examCode, content, load.data],
  );

  const start = (key: string, started: string, work: () => Promise<unknown>) =>
    action.run(key, async () => {
      await work();
      setPollAv(true);
      toast.success(started);
      load.reload();
    });

  const voice = () => {
    const runner =
      kind === "slide_deck"
        ? regenerateSlideAv
        : kind === "podcast"
          ? generatePodcastAudio
          : generateSummaryPodcast;
    return start("voice", "Voicing started", () => runner(itemId));
  };

  // Only a blog is rewritten from a brief here; spoken kinds are produced by the agent.
  const runGenerate = () => {
    if (!prompt.trim()) return undefined;
    return action.run("generate", async () => {
      const generated = await generateBlog(prompt.trim(), examCode.trim() || null);
      if (generatedTitle(generated)) setTitle(generatedTitle(generated));
      if (typeof generated.summary === "string") {
        setSummary(generated.summary);
      }
      const { title: _t, summary: _s, ...rest } = generated;
      setContent((prev) => mergeContent(prev, rest));
      toast.success("Draft generated", "Review and save.");
    });
  };

  const contentForm = () => {
    if (!isMediaKind(kind)) return null;
    // The server replaces a published item's content rather than editing it in place,
    // so its form is read only; title, summary and exam still save.
    if (load.data?.status === "published") {
      return (
        <div className="flex flex-col gap-3">
          <p className="text-osce-meta text-ink-subtle">
            Published items can&apos;t be edited. The title, summary and exam can still change.
          </p>
          <fieldset disabled className="contents">
            {editableForm(kind)}
          </fieldset>
        </div>
      );
    }
    return editableForm(kind);
  };

  const editableForm = (of: MediaKind) => {
    switch (of) {
      case "summary":
        return (
          <SummaryContentForm
            content={content}
            onChange={setContent}
            itemId={itemId}
            itemTitle={title}
          />
        );
      case "blog":
        return <BlogContentForm content={content} onChange={setContent} />;
      case "slide_deck":
        return (
          <B2cSlideDeckForm content={content} onChange={setContent} />
        );
      case "podcast":
        return (
          <PodcastContentForm content={content} onChange={setContent} />
        );
      default:
        return null;
    }
  };

  if (load.loading && !load.data) {
    return <p className="text-osce-meta text-ink-subtle">Loading…</p>;
  }

  if (load.error) {
    return (
      <div className="flex flex-col gap-4">
        <Button variant="ghost" size="sm" className="gap-2" onClick={() => onBack()}>
          <HiOutlineArrowLeft className="h-4 w-4" aria-hidden />
          Back
        </Button>
        <Alert tone="danger">{errorMessage(load.error)}</Alert>
        <div>
          <Button variant="secondary" size="sm" onClick={() => load.reload()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  const item = load.data;
  if (!item) return null;

  const isDraft = item.status === "draft";
  const spoken = isSpokenKind(kind);
  const steps = reviewSteps(kind, content, !isDraft);
  const current = step ?? "draft";
  const review = reviewOf(content);
  const status = avStatus(content);
  const locked = unsaved || action.busy !== null || isAvRunning(status);
  // A step's button keeps saying it is working until its background job settles,
  // not only while the request that started it is in flight.
  const working = {
    facts: action.busy === "check-facts" || status === "checking_facts",
    script: action.busy === "write-script" || status === "writing_script",
    voice: action.busy === "voice" || (status?.startsWith("generating") ?? false),
    produce: action.busy === "produce" || status === "producing",
  };
  const drafted = steps[0]?.state === "done";
  const next = nextAction(kind, content, { published: !isDraft, unsaved });
  const publish = () =>
    action.run("publish", async () => {
      await publishMedia(itemId);
      toast.success("Published");
      load.reload();
    });
  // Nothing reaches learners, or is taken from them, without being asked twice.
  const confirmed = async () => {
    const verb = confirm;
    if (!verb) return;
    const ok = await (verb === "publish"
      ? publish()
      : verb === "save-publish"
        ? save(true)
        : verb === "unpublish"
          ? action.run("unpublish", async () => {
              await unpublishMedia(itemId);
              toast.success("Unpublished");
            })
          : action.run("unlock", async () => {
              await unlockMedia(itemId);
              toast.success("Released");
            }));
    if (ok) setConfirm(null);
  };
  const writeScript = (rewrite: boolean) =>
    start("write-script", "Script check started", () => writeMediaScript(itemId, rewrite));

  const nextButton = () => {
    const run = (label: string, busyKey: string, onClick: () => unknown) => (
      <Button
        size="sm"
        disabled={busyKey === "save" ? !title.trim() || action.busy !== null : locked}
        isLoading={action.busy === busyKey}
        onClick={() => void onClick()}
      >
        {label}
      </Button>
    );
    switch (next.id) {
      case "save":
        return run("Save", "save", () => save());
      case "check-facts":
        return run("Check facts", "check-facts", () =>
          start("check-facts", "Fact check started", () => checkMediaFacts(itemId)),
        );
      case "rule":
        return current === "facts" ? null : run("Review claims", "", () => setStep("facts"));
      case "write-script":
        return run("Write script", "write-script", () => writeScript(false));
      case "check-script":
        return run("Check script", "write-script", () => writeScript(false));
      case "voice":
        return run("Approve and voice", "voice", voice);
      case "publish":
        return run("Publish", "publish", () => setConfirm("publish"));
      case "preview":
        return previewHref ? (
          <Link href={previewHref} target="_blank" rel="noreferrer" className="inline-flex">
            <Button size="sm" variant="secondary">
              Preview as learner
            </Button>
          </Link>
        ) : null;
      default:
        return null;
    }
  };

  const details = (open: boolean) => (
    <Panel title="Details" defaultOpen={open}>
      <div className="flex flex-col gap-4">
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Input
          label="Summary"
          hint="Shown on the list card."
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
        <AuthoringExamField value={examCode} onChange={setExamCode} />
      </div>
    </Panel>
  );
  const produceForm = (
    <ProduceForm
      key={review.brief?.brief ?? ""}
      brief={review.brief}
      hint="The agent drafts, checks the facts, finds pictures and writes the script, then stops before voicing."
      locked={locked}
      working={working.produce}
      primary={next.id === "produce"}
      onProduce={(brief) =>
        start("produce", "Agent started", () => produceMedia(itemId, { brief }))
      }
    />
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <AuthoringIconAction variant="ghost" label="Back to list" onClick={backToList}>
            <HiOutlineArrowLeft className="h-4 w-4" aria-hidden />
          </AuthoringIconAction>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-osce-title font-semibold text-ink">
                {title.trim() || kindLabel}
              </h1>
              <Badge tone={item.status === "published" ? "success" : "warning"}>
                {item.status}
              </Badge>
            </div>
            <p className="mt-1 text-osce-meta text-ink-subtle">
              {kindLabel} · {item.slug} ·{" "}
              {examCode.trim() ? examCode.toUpperCase() : "Any exam"}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          {previewHref && item.status === "published" ? (
            <AuthoringIconAction variant="ghost" label="Preview as learner" href={previewHref}>
              <HiOutlineEye className="h-4 w-4" aria-hidden />
            </AuthoringIconAction>
          ) : null}
          {!isDraft ? (
            <AuthoringIconAction
              variant="ghost"
              label="Unpublish"
              disabled={action.busy !== null}
              onClick={() => setConfirm("unpublish")}
            >
              <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
            </AuthoringIconAction>
          ) : null}
          {isAvRunning(status) ? (
            <AuthoringIconAction
              variant="ghost"
              label="Release stuck job"
              disabled={action.busy !== null}
              onClick={() => setConfirm("unlock")}
            >
              <HiOutlineLockOpen className="h-4 w-4" aria-hidden />
            </AuthoringIconAction>
          ) : null}
          {isDraft ? (
            <AuthoringIconAction variant="ghost" label="Edit as JSON" onClick={() => setJsonOpen(true)}>
              <HiOutlineCodeBracket className="h-4 w-4" aria-hidden />
            </AuthoringIconAction>
          ) : null}
          {isDraft ? (
            <AuthoringIconAction
              variant="danger"
              label="Delete draft"
              disabled={action.busy !== null}
              onClick={() => setDeleteOpen(true)}
            >
              <HiOutlineTrash className="h-4 w-4" aria-hidden />
            </AuthoringIconAction>
          ) : null}
          {/* A blog has no pipeline, so it keeps its save buttons here. */}
          {!spoken ? (
            <>
              <span className="mx-1 hidden h-6 border-l border-border sm:block" aria-hidden />
              {unsaved ? (
                <span className="text-osce-meta text-ink-subtle">Unsaved changes</span>
              ) : null}
              {isDraft ? (
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!title.trim() || action.busy !== null}
                  isLoading={action.busy === "save-publish"}
                  onClick={() => setConfirm("save-publish")}
                >
                  {action.busy === "save-publish" ? "Publishing…" : "Save and publish"}
                </Button>
              ) : null}
              <Button
                size="sm"
                disabled={!title.trim() || action.busy !== null}
                isLoading={action.busy === "save"}
                onClick={() => save()}
              >
                {action.busy === "save" ? "Saving…" : "Save"}
              </Button>
            </>
          ) : null}
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteOpen}
        tone="danger"
        title="Delete this draft?"
        message={`"${title.trim() || kindLabel}" will be removed. This cannot be undone.`}
        confirmText="Delete draft"
        isLoading={action.busy === "delete"}
        error={action.error}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() =>
          void action.run("delete", async () => {
            await deleteMedia(itemId);
            toast.success("Deleted");
            backToList();
          })
        }
      />

      <ConfirmModal
        isOpen={confirm !== null && confirm !== "hand-check"}
        tone={confirm === "unpublish" || confirm === "unlock" ? "danger" : "default"}
        title={
          confirm === "unpublish"
            ? "Unpublish this?"
            : confirm === "unlock"
              ? "Release this job?"
              : "Publish this?"
        }
        message={
          confirm === "unpublish"
            ? "Learners lose it and it goes back to a draft you can edit or delete."
            : confirm === "unlock"
              ? "Only if the worker has died. The item is marked failed so you can start it again."
              : `"${title.trim() || kindLabel}" will be visible to learners straight away.`
        }
        confirmText={
          confirm === "unpublish" ? "Unpublish" : confirm === "unlock" ? "Release" : "Publish"
        }
        isLoading={action.busy !== null}
        error={action.error}
        onCancel={() => {
          setConfirm(null);
          action.clearError();
        }}
        onConfirm={() => void confirmed()}
      />
      <HandCheckModal
        open={confirm === "hand-check"}
        busy={action.busy === "hand-check"}
        error={action.error}
        onClose={() => {
          setConfirm(null);
          action.clearError();
        }}
        onSubmit={(claims) =>
          void action
            .run("hand-check", async () => {
              await recordHandCheck(itemId, claims);
              toast.success("Check recorded");
            })
            .then((ok) => {
              if (ok) setConfirm(null);
            })
        }
      />

      {action.error && confirm === null ? <Alert tone="danger">{action.error}</Alert> : null}

      <ContentJsonEditor
        open={jsonOpen}
        content={content}
        onClose={() => setJsonOpen(false)}
        onSave={(parsed) => setContent((prev) => mergeContent(prev, parsed))}
      />

      {!spoken ? (
        <>
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          {details(true)}

          {isDraft ? (
          <Panel title="Rewrite the draft from a brief" padding="sm">
            <div className="flex flex-col gap-3">
              <Textarea
                aria-label="Prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
                placeholder="Paste the case, notes or topic…"
              />
              <Button
                variant="secondary"
                size="sm"
                disabled={!prompt.trim() || (action.busy !== null && action.busy !== "generate")}
                isLoading={action.busy === "generate"}
                onClick={() => runGenerate()}
              >
                {action.busy === "generate" ? "Generating…" : `Generate ${kindLabel.toLowerCase()}`}
              </Button>
            </div>
          </Panel>
          ) : null}
        </div>

        <Panel title="Content">{contentForm()}</Panel>
        </>
      ) : (
        <>
          <StepGuide steps={steps} current={current} onSelect={setStep} line={next.line} working={next.id === "wait"}>
            {nextButton()}
          </StepGuide>
          {review.error ? (
            <Alert tone="danger">
              The last {ERROR_STEPS[review.error.step] ?? review.error.step} failed:{" "}
              {review.error.message}
            </Alert>
          ) : null}
          {review.run ? (
            <RunLog
              run={review.run}
              running={status === "producing"}
              stopping={action.busy === "stop"}
              onStop={() =>
                void action.run("stop", async () => {
                  await stopProduce(itemId);
                  load.reload();
                })
              }
            />
          ) : null}

          {current === "draft" ? (
            // Remounted once a draft exists, so its panels open and fold the right way round.
            <div key={String(drafted)} className="flex flex-col gap-6">
              {drafted ? null : (
                <Panel title="What should it cover?" padding="sm">
                  {produceForm}
                </Panel>
              )}
              <Panel title="Content" defaultOpen={drafted}>
                {contentForm()}
              </Panel>
              {details(false)}
              {drafted ? (
                <Panel title="Produce again from a brief" padding="sm" defaultOpen={false}>
                  {produceForm}
                </Panel>
              ) : null}
            </div>
          ) : null}
          {current === "facts" ? (
            <Panel title="Check the facts">
              <FactCheck
                facts={review.facts}
                rulings={
                  // A ruling made while the agent or a job runs would be overwritten when it settles.
                  isAvRunning(status)
                    ? undefined
                    : {
                        onAccept: (claim, swap) =>
                          setContent(acceptSuggestion(content, claim, swap)),
                        onDismiss: (claim) => setContent(dismissSuggestion(content, claim)),
                        onReopen: (claim) => setContent(reopenSuggestion(content, claim)),
                      }
                }
                locked={locked}
                working={working.facts}
                onCheck={() =>
                  start("check-facts", "Fact check started", () => checkMediaFacts(itemId))
                }
              />
              {isAvRunning(status) ? null : (
                <div className="mt-4">
                  <Button variant="ghost" size="sm" onClick={() => setConfirm("hand-check")}>
                    Record a check done by hand
                  </Button>
                </div>
              )}
            </Panel>
          ) : null}
          {current === "script" ? (
            <Panel title="Script">
              <ScriptStep
                kind={kind}
                content={content}
                onChange={setContent}
                locked={locked}
                onWrite={writeScript}
              />
            </Panel>
          ) : null}
          {current === "voice" ? (
            <Panel title="Voice">
              <VoiceStep
                kind={kind}
                content={content}
                locked={locked}
                working={working.voice}
                voiced={steps.find((entry) => entry.id === "voice")?.state === "done"}
                onVoice={voice}
              />
            </Panel>
          ) : null}
          {current === "publish" ? (
            <Panel title="Publish">
              <PublishStep steps={steps} />
            </Panel>
          ) : null}
        </>
      )}
    </div>
  );
}
