"use client";

import { useState } from "react";
import { Checkbox, Input, Textarea } from "@/foundation/ui";
import {
  mergeContent,
  setSpecialties,
  specialtiesFromContent,
  stringListField,
} from "@/capabilities/staff-media/content/b2cMediaShapes";
import { MEDICAL_SPECIALTY_NAMES } from "@/capabilities/staff-media/content/medicalSpecialties";
import { StringListField } from "@/capabilities/staff-media/forms/StringListField";
import { PodcastPlayer, type Episode } from "@/capabilities/media/PodcastPlayer";

export function SummaryContentForm({
  content,
  onChange,
  itemId,
  itemTitle,
}: {
  content: Record<string, unknown>;
  onChange: (content: Record<string, unknown>) => void;
  itemId: string;
  itemTitle: string;
}) {
  const [episodeIndex, setEpisodeIndex] = useState(0);
  const patch = (partial: Record<string, unknown>) => onChange(mergeContent(content, partial));

  const setList = (key: string, items: string[]) => {
    onChange(mergeContent(content, { [key]: items.filter((line) => line.trim()) }));
  };

  const bodyMd = typeof content.body_md === "string" ? content.body_md : "";
  const podcastUrl =
    typeof content.podcast_url === "string" && content.podcast_url.trim()
      ? content.podcast_url.trim()
      : null;

  const selected = specialtiesFromContent(content);

  const toggleSpecialty = (name: string) => {
    const next = selected.includes(name)
      ? selected.filter((s) => s !== name)
      : [...selected, name];
    onChange(setSpecialties(content, next));
  };

  const episodes: Episode[] = podcastUrl
    ? [{ id: itemId, title: itemTitle, url: podcastUrl }]
    : [];

  return (
    <div className="flex flex-col gap-5">
      <StringListField
        label="Red flags"
        items={stringListField(content, "red_flags")}
        onChange={(items) => setList("red_flags", items)}
      />
      <StringListField
        label="Examinations"
        items={stringListField(content, "examinations")}
        onChange={(items) => setList("examinations", items)}
      />
      <StringListField
        label="Brief management"
        items={stringListField(content, "brief_management")}
        onChange={(items) => setList("brief_management", items)}
      />
      <StringListField
        label="Psychosocial aspects"
        items={stringListField(content, "psychosocial_aspects")}
        onChange={(items) => setList("psychosocial_aspects", items)}
      />
      <div className="flex flex-col gap-2">
        <span className="text-osce-meta font-medium text-ink-muted">Specialties</span>
        <div className="max-h-48 overflow-y-auto rounded-osce-md border border-border p-3">
          <ul className="grid gap-2 sm:grid-cols-2">
            {MEDICAL_SPECIALTY_NAMES.map((name) => (
              <li key={name}>
                <Checkbox
                  label={name}
                    checked={selected.includes(name)}
                    onChange={() => toggleSpecialty(name)}
                  />
              </li>
            ))}
          </ul>
        </div>
      </div>
      <Textarea
        label="Body (markdown, optional)"
          value={bodyMd}
          onChange={(e) => patch({ body_md: e.target.value })}
          rows={8}
          className="font-mono"
        />
      <Input
        label="Podcast URL"
        value={typeof content.podcast_url === "string" ? content.podcast_url : ""}
        onChange={(e) => patch({ podcast_url: e.target.value })}
      />
      {podcastUrl ? (
        <div className="rounded-osce-md border border-border p-4">
          <PodcastPlayer
            episodes={episodes}
            index={episodeIndex}
            onIndexChange={setEpisodeIndex}
            heading="meta"
          />
        </div>
      ) : null}
    </div>
  );
}
