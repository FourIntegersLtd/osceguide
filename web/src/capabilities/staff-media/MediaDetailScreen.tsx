"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { HiOutlineArrowLeft } from "react-icons/hi2";
import { Alert, Badge, Button, ConfirmModal, Input, Panel, Textarea } from "@/foundation/ui";
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
  firstOpenStep,
  isSpokenKind,
  reviewOf,
  reviewSteps,
  type StepId,
} from "@/capabilities/staff-media/content/review";
import { ERROR_STEPS, ProduceForm, RunLog } from "@/capabilities/fact-check";
import { ContentJsonEditor } from "@/capabilities/staff-media/parts/ContentJsonEditor";
import { FactCheck } from "@/capabilities/fact-check";
import {
  ScriptStep,
  StepNav,
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
  regenerateSlideAv,
  stopProduce,
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
    // Open on the first step still to do, and stay where the reader then goes.
    const opened = firstOpenStep(load.data.kind, contentRecord(load.data));
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
      await updateMedia(itemId, {
        title: title.trim(),
        summary: summary.trim() || null,
        content,
      });
      if (andPublish) {
        await publishMedia(itemId);
        toast.success("Saved and published");
      } else {
        toast.success("Saved");
      }
      load.reload();
    });

  // A check or a voicing reads what is stored, so the panel holds its buttons
  // back while the form is ahead of the server.
  const unsaved = useMemo(
    () =>
      JSON.stringify(content) !== JSON.stringify(contentRecord(load.data)),
    [content, load.data],
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
    switch (kind) {
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
      </div>
    );
  }

  const item = load.data;
  if (!item) return null;

  const isDraft = item.status === "draft";
  const spoken = isSpokenKind(kind);
  const steps = reviewSteps(kind, content);
  const current = step ?? "draft";
  const position = steps.findIndex((entry) => entry.id === current);
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
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" className="gap-2" onClick={backToList}>
          <HiOutlineArrowLeft className="h-4 w-4" aria-hidden />
          Back to list
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          {isDraft ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={action.busy !== null}
              onClick={() => setDeleteOpen(true)}
            >
              Delete draft
            </Button>
          ) : null}
          <Button variant="ghost" size="sm" onClick={() => setJsonOpen(true)}>
            Edit as JSON
          </Button>
          <span className="hidden h-6 border-l border-border sm:block" aria-hidden />
          {unsaved ? (
            <span className="text-osce-meta text-ink-subtle">Unsaved changes</span>
          ) : null}
          {previewHref && item.status === "published" ? (
            <Link
              href={previewHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex"
            >
              <Button variant="secondary" size="sm">
                Preview as learner
              </Button>
            </Link>
          ) : null}
          {kind === "blog" ? (
            <Button
              variant="secondary"
              size="sm"
              disabled={!title.trim() || action.busy !== null}
              isLoading={action.busy === "save-publish"}
              onClick={() => save(true)}
            >
              {action.busy === "save-publish" ? "Publishing…" : "Save and publish"}
            </Button>
          ) : isDraft ? (
            <Button
              variant="secondary"
              size="sm"
              disabled={unsaved || action.busy !== null}
              onClick={() =>
                action.run("publish", async () => {
                  await publishMedia(itemId);
                  toast.success("Published");
                  load.reload();
                })
              }
              isLoading={action.busy === "publish"}
            >
              {action.busy === "publish" ? "Publishing…" : "Publish"}
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
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteOpen}
        tone="danger"
        title="Delete this draft?"
        message={`"${title.trim() || kindLabel}" will be removed. This cannot be undone.`}
        confirmText="Delete draft"
        isLoading={action.busy === "delete"}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() =>
          void action.run("delete", async () => {
            await deleteMedia(itemId);
            toast.success("Deleted");
            backToList();
          })
        }
      />

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
      {pollAv ? (
        <Alert tone="info">
          Working on it… this page updates when it finishes.
        </Alert>
      ) : null}

      <ContentJsonEditor
        open={jsonOpen}
        content={content}
        onClose={() => setJsonOpen(false)}
        onSave={(parsed) => setContent((prev) => mergeContent(prev, parsed))}
      />

      <div>
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

      {!spoken ? (
        <>
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <Panel
            title="Details"
            description="The exam is fixed when the item is created."
          >
            <div className="flex flex-col gap-4">
              <Input
                label="Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <Input
                label="Summary"
                hint="Shown on the list card."
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
              />
            </div>
          </Panel>

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
        </div>

        <Panel title="Content">{contentForm()}</Panel>
        </>
      ) : (
        <>
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
          <StepNav steps={steps} current={current} onSelect={setStep} />
          {review.error ? (
            <Alert tone="danger">
              The last {ERROR_STEPS[review.error.step] ?? review.error.step} failed:{" "}
              {review.error.message}
            </Alert>
          ) : null}
          {unsaved && current !== "draft" ? (
            <Alert tone="info">
              You have unsaved changes. Save before checking or voicing, so the check reads what you
              see.
            </Alert>
          ) : null}

          {current === "draft" ? (
            <>
          <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <Panel
              title="Details"
              description="The exam is fixed when the item is created."
            >
              <div className="flex flex-col gap-4">
                <Input
                  label="Title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                <Input
                  label="Summary"
                  hint="Shown on the list card."
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                />
              </div>
            </Panel>

            <Panel title="Produce with the agent" padding="sm">
              <ProduceForm
                key={review.brief?.brief ?? ""}
                brief={review.brief}
                hint="What to teach and for which exam. The agent drafts, checks the facts, finds pictures and writes the script, then stops before voicing."
                locked={locked}
                working={working.produce}
                onProduce={(brief) =>
                  start("produce", "Agent started", () =>
                    produceMedia(itemId, { brief }),
                  )
                }
              />
            </Panel>
          </div>

          <Panel title="Content">{contentForm()}</Panel>
            </>
          ) : null}
          {current === "facts" ? (
            <Panel title="Step 2: Check the facts">
              <FactCheck
                facts={review.facts}
                rulings={{
                  onAccept: (claim, swap) =>
                    setContent(acceptSuggestion(content, claim, swap)),
                  onDismiss: (claim) => setContent(dismissSuggestion(content, claim)),
                  onReopen: (claim) => setContent(reopenSuggestion(content, claim)),
                }}
                locked={locked}
                working={working.facts}
                onCheck={() =>
                  start("check-facts", "Fact check started", () => checkMediaFacts(itemId))
                }
              />
            </Panel>
          ) : null}
          {current === "script" ? (
            <Panel title="Step 3: Write and check the script">
              <ScriptStep
                kind={kind}
                content={content}
                onChange={setContent}
                locked={locked}
                working={working.script}
                onWrite={(rewrite) =>
                  start("write-script", "Script check started", () =>
                    writeMediaScript(itemId, rewrite),
                  )
                }
              />
            </Panel>
          ) : null}
          {current === "voice" ? (
            <Panel title="Step 4: Approve and voice">
              <VoiceStep
                kind={kind}
                content={content}
                locked={locked}
                working={working.voice}
                steps={steps}
                onVoice={voice}
              />
            </Panel>
          ) : null}

          <div className="flex justify-between gap-2">
            <Button
              variant="ghost"
              size="sm"
              disabled={position === 0}
              onClick={() => setStep(steps[position - 1]?.id ?? current)}
            >
              Back
            </Button>
            {position < steps.length - 1 ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setStep(steps[position + 1]?.id ?? current)}
              >
                Next: {steps[position + 1]?.label}
              </Button>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
