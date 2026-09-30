"use client";

import { Prose } from "@/capabilities/media/Prose";

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
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium text-ink">Article body (markdown)</span>
        <textarea
          value={bodyMd}
          onChange={(e) => onChange({ ...content, body_md: e.target.value })}
          rows={18}
          className="rounded-control border border-border-strong bg-surface px-3 py-2 font-mono text-sm"
        />
      </label>
      <div className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium text-ink">Preview</span>
        <div className="min-h-[12rem] rounded-control border border-border bg-surface-raised p-4">
          {bodyMd.trim() ? <Prose content={bodyMd} /> : <p className="text-ink-subtle">Nothing to preview yet.</p>}
        </div>
      </div>
    </div>
  );
}
