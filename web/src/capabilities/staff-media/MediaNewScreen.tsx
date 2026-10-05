"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Input,
  Modal,
  Select,
  Textarea,
  getInputClassName,
} from "@/foundation/ui";
import {
  MEDIA_KIND_LABELS,
  MEDIA_KINDS,
  isMediaKind,
  type MediaKind,
} from "@/capabilities/media/api";
import { AuthoringExamSelect } from "@/capabilities/authoring/parts/AuthoringExamSelect";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import {
  createMedia,
  generateBlog,
  generatedTitle,
  produceMedia,
} from "@/capabilities/staff-media/api";
import { isSpokenKind } from "@/capabilities/staff-media/content/review";
import { mergeContent } from "@/capabilities/staff-media/content/b2cMediaShapes";
import { emptyContentForKind } from "@/capabilities/staff-media/contentScaffolds";
import { staffMediaDetailPath } from "@/capabilities/staff-media/paths";

export function MediaNewForm({
  initialKind,
  onCancel,
  onCreated,
}: {
  initialKind: MediaKind;
  onCancel?: () => void;
  onCreated: (itemId: string) => void;
}) {
  const [kind, setKind] = useState<MediaKind>(initialKind);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [source, setSource] = useState("");
  const [examCode, setExamCode] = useState("");
  const action = useAction();

  useEffect(() => {
    setKind(initialKind);
  }, [initialKind]);

  const kindLabel = MEDIA_KIND_LABELS[kind].one;
  // A spoken kind is produced by the agent after the item exists; a blog is drafted inline first,
  // so a failed write leaves nothing behind.
  const produced = isSpokenKind(kind);
  const ready = produced
    ? Boolean(title.trim()) && (!brief.trim() || brief.trim().length >= 8)
    : Boolean(title.trim() || brief.trim());

  const create = () =>
    action.run("create", async () => {
      const exam = examCode.trim() || null;
      const written =
        !produced && brief.trim() ? await generateBlog(brief.trim(), exam) : {};
      const { title: _title, summary: writtenSummary, ...rest } = written;
      const named =
        title.trim() ||
        generatedTitle(written) ||
        `Untitled ${kindLabel.toLowerCase()}`;
      const content = mergeContent(emptyContentForKind(kind), rest);
      if (kind === "slide_deck" && !content.topic) content.topic = named;
      const item = await createMedia({
        kind,
        title: named,
        exam_code: exam,
        summary:
          typeof writtenSummary === "string" && writtenSummary.trim()
            ? writtenSummary.trim()
            : null,
        content,
      });
      if (produced && brief.trim()) {
        await produceMedia(item.id, {
          brief: brief.trim(),
          source_text: source.trim() || null,
        });
      }
      onCreated(item.id);
    });

  return (
    <div className="flex flex-col gap-4">
      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <Select
        label="Kind"
        value={kind}
        onChange={(e) => {
          const next = e.target.value;
          if (isMediaKind(next)) setKind(next);
        }}
      >
        {MEDIA_KINDS.map((k) => (
          <option key={k} value={k}>
            {MEDIA_KIND_LABELS[k].one}
          </option>
        ))}
      </Select>
      <Input
        label="Title"
        hint={
          produced
            ? "The agent writes to this title."
            : "Leave empty to take the title from the draft."
        }
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <label className="flex flex-col gap-1.5">
        <span className="text-osce-meta font-medium text-ink-muted">Exam</span>
        <AuthoringExamSelect
          value={examCode}
          onChange={setExamCode}
          allowEmpty
          emptyLabel="Any exam"
          className={getInputClassName()}
        />
      </label>
      <Textarea
        label="What should it cover?"
        hint={
          produced
            ? "What to teach. The agent drafts, checks the facts, finds pictures and writes the script, then stops before voicing. Leave it empty to start from a blank item."
            : "Paste the case, your notes or the topic. The first draft is written from this; leave it empty to start from a blank item."
        }
        rows={produced ? 4 : 8}
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
      />
      {produced ? (
        <Textarea
          label="Source case (optional)"
          hint="Pasted whole. The agent changes the patient's details and lists what it adds."
          rows={6}
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
      ) : null}
      <div className="flex justify-end gap-2 pt-1">
        {onCancel ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            disabled={action.busy === "create"}
            onClick={onCancel}
          >
            Cancel
          </Button>
        ) : null}
        <Button
          size="sm"
          disabled={!ready || action.busy === "create"}
          onClick={() => create()}
        >
          {action.busy === "create"
            ? brief.trim() && !produced
              ? "Writing the draft…"
              : "Creating…"
            : brief.trim()
              ? produced
                ? "Create and produce"
                : "Create and write draft"
              : `Create ${kindLabel.toLowerCase()}`}
        </Button>
      </div>
    </div>
  );
}

export function MediaNewModal({
  open,
  initialKind,
  onClose,
  onCreated,
}: {
  open: boolean;
  initialKind: MediaKind;
  onClose: () => void;
  onCreated?: (itemId: string) => void;
}) {
  const router = useRouter();
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    if (open) setFormKey((key) => key + 1);
  }, [open]);

  if (!open) return null;

  const kindLabel = MEDIA_KIND_LABELS[initialKind].one;

  return (
    <Modal
      onClose={onClose}
      title={`New ${kindLabel.toLowerCase()}`}
      width="min(32rem, 96vw)"
    >
      <div className="p-4 lg:p-6">
        <MediaNewForm
          key={formKey}
          initialKind={initialKind}
          onCancel={onClose}
          onCreated={(itemId) => {
            onCreated?.(itemId);
            onClose();
            router.push(staffMediaDetailPath(itemId));
          }}
        />
      </div>
    </Modal>
  );
}
