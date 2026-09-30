"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Alert, Button, Input, Modal } from "@/foundation/ui";
import { MEDIA_KIND_LABELS, MEDIA_KINDS, isMediaKind, type MediaKind } from "@/capabilities/media/api";
import { AuthoringExamSelect } from "@/capabilities/authoring/parts/AuthoringExamSelect";
import { useAction } from "@/capabilities/authoring/parts/useAction";
import { createMedia } from "@/capabilities/staff-media/api";
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
  const [summary, setSummary] = useState("");
  const [examCode, setExamCode] = useState("");
  const action = useAction();

  useEffect(() => {
    setKind(initialKind);
  }, [initialKind]);

  const kindLabel = MEDIA_KIND_LABELS[kind].one;

  return (
    <div className="flex flex-col gap-4">
      {action.error ? <Alert tone="danger">{action.error}</Alert> : null}

      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium text-ink">Kind</span>
        <select
          value={kind}
          onChange={(e) => {
            const next = e.target.value;
            if (isMediaKind(next)) setKind(next);
          }}
          className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
        >
          {MEDIA_KINDS.map((k) => (
            <option key={k} value={k}>{MEDIA_KIND_LABELS[k].one}</option>
          ))}
        </select>
      </label>
      <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium text-ink">Exam</span>
        <AuthoringExamSelect
          value={examCode}
          onChange={setExamCode}
          allowEmpty
          emptyLabel="Any exam"
          className="w-full rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
        />
      </label>
      <Input label="Summary (optional)" value={summary} onChange={(e) => setSummary(e.target.value)} />
      <div className="flex justify-end gap-2 pt-1">
        {onCancel ? (
          <Button type="button" variant="ghost" size="sm" disabled={action.busy === "create"} onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
        <Button
          size="sm"
          disabled={!title.trim() || action.busy === "create"}
          onClick={() =>
            void action.run("create", async () => {
              const scaffold = emptyContentForKind(kind);
              if (kind === "slide_deck") {
                scaffold.topic = title.trim();
              }
              const item = await createMedia({
                kind,
                title: title.trim(),
                exam_code: examCode.trim() || null,
                summary: summary.trim() || null,
                content: scaffold,
              });
              onCreated(item.id);
            })
          }
        >
          {action.busy === "create" ? "Creating…" : `Create ${kindLabel.toLowerCase()}`}
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
