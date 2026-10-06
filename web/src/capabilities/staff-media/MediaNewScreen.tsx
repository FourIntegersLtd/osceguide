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
} from "@/foundation/ui";
import {
  MEDIA_KIND_LABELS,
  MEDIA_KINDS,
  isMediaKind,
  type MediaKind,
} from "@/capabilities/media/api";
import { AuthoringExamField } from "@/capabilities/authoring/parts/AuthoringExamField";
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
  initialExam = "",
  onCancel,
  onCreated,
}: {
  initialKind: MediaKind;
  /** The list's exam filter, so a new item lands where the reader is looking. */
  initialExam?: string;
  onCancel?: () => void;
  onCreated: (itemId: string) => void;
}) {
  const [kind, setKind] = useState<MediaKind>(initialKind);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [examCode, setExamCode] = useState(initialExam);
  const action = useAction();

  useEffect(() => {
    setKind(initialKind);
  }, [initialKind]);

  const kindLabel = MEDIA_KIND_LABELS[kind].one;
  // A spoken kind is produced by the agent after the item exists; a blog is drafted inline first,
  // so a failed write leaves nothing behind.
  const produced = isSpokenKind(kind);
  // Nothing typed starts a blank "Untitled …" item; a brief for the agent needs enough to go on.
  const ready = !produced || !brief.trim() || brief.trim().length >= 8;

  const create = () =>
    action.run("create", async () => {
      const exam = examCode.trim() || null;
      const written =
        !produced && brief.trim() ? await generateBlog(brief.trim(), exam) : {};
      const { title: _title, summary: writtenSummary, ...rest } = written;
      const named =
        title.trim() ||
        generatedTitle(written) ||
        // Stamped, since the slug comes from the title and a second "Untitled summary" would clash.
        `Untitled ${kindLabel.toLowerCase()} ${new Date().toLocaleString("en-GB", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}`;
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
        await produceMedia(item.id, { brief: brief.trim() });
      }
      onCreated(item.id);
    });

  return (
    <div className="flex flex-col gap-4">
      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <Textarea
        label="What should it cover?"
        hint="A topic, your notes or a case pasted whole. Leave it empty to start from a blank item."
        rows={8}
        value={brief}
        onChange={(e) => setBrief(e.target.value)}
      />
      {/* Kind and exam come from the tab and filter the list was on; change them here. */}
      <details className="rounded-osce-md border border-border px-3 py-2">
        <summary className="cursor-pointer text-osce-meta text-ink-muted">
          {kindLabel} · {examCode.trim() ? examCode.toUpperCase() : "Any exam"} ·{" "}
          {title.trim() || "title from the draft"}
        </summary>
        <div className="mt-3 flex flex-col gap-4">
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
            hint="Leave empty to take the title from the draft."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <AuthoringExamField value={examCode} onChange={setExamCode} />
        </div>
      </details>
      {brief.trim() ? (
        <p className="text-osce-meta text-ink-subtle">
          {produced
            ? "The agent drafts it, checks the facts, finds pictures and writes the script, then stops before voicing. From a case it keeps only the diagnosis and management and invents the patient."
            : "The first draft is written from this."}
        </p>
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
            : "Create"}
        </Button>
      </div>
    </div>
  );
}

export function MediaNewModal({
  open,
  initialKind,
  initialExam,
  onClose,
  onCreated,
}: {
  open: boolean;
  initialKind: MediaKind;
  initialExam?: string;
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
          initialExam={initialExam}
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
