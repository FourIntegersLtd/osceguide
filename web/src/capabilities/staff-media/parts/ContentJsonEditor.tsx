"use client";

import { useEffect, useState } from "react";
import { Button, Modal } from "@/foundation/ui";

export function ContentJsonEditor({
  open,
  content,
  onClose,
  onSave,
}: {
  open: boolean;
  content: Record<string, unknown>;
  onClose: () => void;
  onSave: (parsed: Record<string, unknown>) => void;
}) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setText(JSON.stringify(content, null, 2));
      setError(null);
    }
  }, [open, content]);

  const save = () => {
    try {
      const parsed = JSON.parse(text) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        setError("Content must be a JSON object.");
        return;
      }
      onSave(parsed as Record<string, unknown>);
      onClose();
    } catch {
      setError("Invalid JSON.");
    }
  };

  if (!open) return null;

  return (
    <Modal onClose={onClose} title="Edit content JSON" width="min(42rem, 96vw)">
      <div className="flex max-h-[70vh] flex-col gap-3 p-4">
        {error ? <p className="text-sm text-osce-danger-text">{error}</p> : null}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={20}
          className="min-h-[240px] flex-1 rounded-control border border-border-strong bg-surface px-3 py-2 font-mono text-xs"
          spellCheck={false}
        />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" onClick={save}>Apply</Button>
        </div>
      </div>
    </Modal>
  );
}
