"use client";

import { Input, Textarea } from "@/foundation/ui";

export function PodcastContentForm({
  content,
  onChange,
}: {
  content: Record<string, unknown>;
  onChange: (content: Record<string, unknown>) => void;
}) {
  const audioUrl = typeof content.audio_url === "string" ? content.audio_url : "";
  const script = typeof content.script === "string" ? content.script : "";

  return (
    <div className="flex flex-col gap-4">
      <Input
        label="Audio URL"
        value={audioUrl}
        onChange={(e) => onChange({ ...content, audio_url: e.target.value })}
        hint="Paste a hosted audio file URL until TTS is wired."
      />
      <Textarea
        label="Script (optional)"
          value={script}
          onChange={(e) => onChange({ ...content, script: e.target.value })}
          rows={12}
        />
    </div>
  );
}
