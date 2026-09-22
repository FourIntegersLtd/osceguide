"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { HiOutlineArrowLeft } from "react-icons/hi2";
import { Alert, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { MEDIA_KIND_LABELS, isMediaKind } from "@/capabilities/media/api";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { avStatus, isAvRunning, mergeContent } from "@/capabilities/staff-media/content/b2cMediaShapes";
import { BlogContentForm } from "@/capabilities/staff-media/forms/BlogContentForm";
import { B2cSlideDeckForm } from "@/capabilities/staff-media/forms/B2cSlideDeckForm";
import { PodcastContentForm } from "@/capabilities/staff-media/forms/PodcastContentForm";
import { SummaryContentForm } from "@/capabilities/staff-media/forms/SummaryContentForm";
import { ContentJsonEditor } from "@/capabilities/staff-media/parts/ContentJsonEditor";
import {
  deleteMedia,
  generateBlog,
  generatePodcast,
  generatePodcastAudio,
  generateSlideDeck,
  generateSummary,
  generateSummaryPodcast,
  publishMedia,
  readMediaById,
  regenerateSlideAv,
  updateMedia,
  type MediaItem,
} from "@/capabilities/staff-media/api";
import { learnerMediaPreviewPath } from "@/capabilities/staff-media/paths";

function contentRecord(item: MediaItem | null): Record<string, unknown> {
  if (!item?.content || typeof item.content !== "object" || Array.isArray(item.content)) return {};
  return item.content as Record<string, unknown>;
}

export function MediaDetailScreen({ itemId, onBack }: { itemId: string; onBack: () => void }) {
  const load = useAsync((signal) => readMediaById(itemId, signal), [itemId]);
  const action = useAction(load.reload);
  const toast = useToast();

  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [examCode, setExamCode] = useState("");
  const [content, setContent] = useState<Record<string, unknown>>({});
  const [prompt, setPrompt] = useState("");
  const [jsonOpen, setJsonOpen] = useState(false);
  const [pollAv, setPollAv] = useState(false);

  useEffect(() => {
    if (!load.data) return;
    setTitle(load.data.title);
    setSummary(load.data.summary ?? "");
    setExamCode(load.data.exam_code ?? "");
    setContent(contentRecord(load.data));
    const status = avStatus(contentRecord(load.data));
    setPollAv(isAvRunning(status));
  }, [load.data]);

  useEffect(() => {
    if (!pollAv) return;
    const id = window.setInterval(() => load.reload(), 5000);
    return () => window.clearInterval(id);
  }, [pollAv, load]);

  useEffect(() => {
    const status = avStatus(content);
    if (!isAvRunning(status)) setPollAv(false);
  }, [content]);

  const kind = load.data?.kind ?? "summary";
  const kindLabel = isMediaKind(kind) ? MEDIA_KIND_LABELS[kind].one : "Item";

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

  const runGenerate = () => {
    if (!prompt.trim() || !isMediaKind(kind)) return;
    const runner =
      kind === "blog"
        ? generateBlog
        : kind === "slide_deck"
          ? generateSlideDeck
          : kind === "podcast"
            ? generatePodcast
            : generateSummary;
    void action.run("generate", async () => {
      const generated = await runner(prompt.trim(), examCode.trim() || null);
      if (typeof generated.title === "string" && generated.title.trim()) {
        setTitle(generated.title.trim());
      }
      if (typeof generated.summary === "string") {
        setSummary(generated.summary);
      }
      const { title: _t, summary: _s, ...rest } = generated;
      setContent((prev) => mergeContent(prev, rest));
      if (kind === "slide_deck" && typeof generated.topic === "string") {
        setContent((prev) => mergeContent(prev, { topic: generated.topic }));
      }
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
          <B2cSlideDeckForm
            content={content}
            onChange={setContent}
            avBusy={action.busy === "regenerate-av"}
            onRegenerateAv={() =>
              void action.run("regenerate-av", async () => {
                await regenerateSlideAv(itemId);
                setPollAv(true);
                toast.success("Regeneration started", "This may take several minutes.");
                load.reload();
              })
            }
          />
        );
      case "podcast":
        return (
          <div className="flex flex-col gap-4">
            <PodcastContentForm content={content} onChange={setContent} />
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={action.busy === "generate-audio" || isAvRunning(avStatus(content))}
              onClick={() =>
                void action.run("generate-audio", async () => {
                  await generatePodcastAudio(itemId);
                  setPollAv(true);
                  toast.success("Audio generation started");
                  load.reload();
                })
              }
            >
              Generate audio (TTS)
            </Button>
          </div>
        );
      default:
        return null;
    }
  };

  if (load.loading && !load.data) {
    return <p className="text-sm text-ink-subtle">Loading…</p>;
  }

  if (load.error) {
    return (
      <div className="space-y-3">
        <Button variant="ghost" size="sm" className="gap-2" onClick={onBack}>
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" className="gap-2" onClick={onBack}>
          <HiOutlineArrowLeft className="h-4 w-4" aria-hidden />
          Back to list
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" onClick={() => setJsonOpen(true)}>Edit JSON</Button>
          {previewHref && item.status === "published" ? (
            <Link href={previewHref} target="_blank" rel="noreferrer" className="inline-flex">
              <Button variant="secondary" size="sm">Preview as learner</Button>
            </Link>
          ) : null}
          {kind === "summary" ? (
            <Button
              size="sm"
              variant="secondary"
              disabled={action.busy === "generate-podcast" || isAvRunning(avStatus(content))}
              onClick={() =>
                void action.run("generate-podcast", async () => {
                  await generateSummaryPodcast(itemId);
                  setPollAv(true);
                  toast.success("Podcast generation started");
                  load.reload();
                })
              }
            >
              Generate podcast
            </Button>
          ) : null}
          {isDraft ? (
            <Button
              size="sm"
              disabled={action.busy !== null}
              onClick={() =>
                void action.run("publish", async () => {
                  await publishMedia(itemId);
                  toast.success("Published");
                  load.reload();
                })
              }
            >
              Publish
            </Button>
          ) : null}
          {kind === "blog" ? (
            <Button
              size="sm"
              disabled={!title.trim() || action.busy !== null}
              onClick={() => void save(true)}
            >
              Save & publish
            </Button>
          ) : null}
          {isDraft ? (
            <Button
              variant="secondary"
              size="sm"
              disabled={action.busy !== null}
              onClick={() =>
                void action.run("delete", async () => {
                  await deleteMedia(itemId);
                  toast.success("Deleted");
                  onBack();
                })
              }
            >
              Delete draft
            </Button>
          ) : null}
          <Button size="sm" disabled={!title.trim() || action.busy === "save"} onClick={() => void save()}>
            Save
          </Button>
        </div>
      </div>

      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}
      {pollAv ? (
        <Alert tone="info">Production in progress… status updates every few seconds.</Alert>
      ) : null}

      <ContentJsonEditor
        open={jsonOpen}
        content={content}
        onClose={() => setJsonOpen(false)}
        onSave={(parsed) => setContent((prev) => mergeContent(prev, parsed))}
      />

      <Card padding="md" className="flex max-w-3xl flex-col gap-4">
        <div>
          <h1 className="text-lg font-semibold text-ink">{kindLabel}</h1>
          <p className="text-xs text-ink-subtle">
            {item.slug}
            {item.exam_code ? ` · ${item.exam_code}` : ""}
            {` · ${item.status}`}
          </p>
        </div>
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <Input label="Summary (list card)" value={summary} onChange={(e) => setSummary(e.target.value)} />
        <p className="text-sm text-ink-subtle">
          Exam: {examCode.trim() ? examCode.toUpperCase() : "Any"} (set at create time)
        </p>
      </Card>

      <Card padding="md" className="flex max-w-3xl flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink">Generate from prompt</h2>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
          placeholder="Describe the topic…"
        />
        <Button variant="secondary" size="sm" disabled={!prompt.trim()} onClick={() => void runGenerate()}>
          Generate {kindLabel.toLowerCase()}
        </Button>
      </Card>

      <Card padding="md" className="max-w-5xl">
        <h2 className="mb-4 text-sm font-semibold text-ink">Content</h2>
        {contentForm()}
      </Card>
    </div>
  );
}
