"use client";

import { Prose } from "@/capabilities/media/Prose";
import { Textarea } from "@/foundation/ui";

export function BlogContentForm({
  content,
  onChange,
}: {
  content: Record<string, unknown>;
  onChange: (content: Record<string, unknown>) => void;
}) {
  const bodyMd = typeof content.body_md === "string" ? content.body_md : "";

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Textarea
        label="Article body (markdown)"
        value={bodyMd}
        onChange={(e) => onChange({ ...content, body_md: e.target.value })}
        rows={18}
        className="font-mono"
      />
      <div className="flex flex-col gap-1.5">
        <span className="text-osce-meta font-medium text-ink-muted">
          Preview
        </span>
        <div className="min-h-[12rem] rounded-osce-md bg-surface-raised p-4 text-osce-body">
          {bodyMd.trim() ? (
            <Prose content={bodyMd} />
          ) : (
            <p className="text-ink-subtle">Nothing to preview yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
