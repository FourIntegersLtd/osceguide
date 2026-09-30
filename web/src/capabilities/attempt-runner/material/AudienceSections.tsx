"use client";

import { useState } from "react";
import { Dropdown } from "@/foundation/table";
import { MarkdownRenderer, Modal } from "@/foundation/ui";
import { B2CSegmentedTabs } from "@/foundation/ui/B2CSegmentedTabs";
import { briefBlockEntries } from "./briefBlockMeta";
import { DoctorInfoBulletList, DoctorInfoSection } from "./DoctorInfoLayout";
import {
  asText,
  humanise,
  isRecord,
  mediaItems,
  type AudienceBlock,
  type AudienceSection,
  type MediaItem,
} from "./sectionsByAudience";

export type { Audience, AudienceBlock, AudienceSection } from "./sectionsByAudience";
export { mediaItems, sectionLines, sectionsFor } from "./sectionsByAudience";

/**
 * How a set of sections is laid out: `brief` is the candidate's reading —
 * every block its own iconed subsection, in the legacy b2c reading order —
 * `open` plain cards, `collapsible` panels for an examiner's model answer,
 * one tab per section for an actor's script.
 */
export type SectionsVariant = "brief" | "open" | "collapsible" | "tabs";

/**
 * A station's content, drawn from its template's own sections and block types
 * rather than by field name or exam, so a new exam's layout is template data.
 * Each block `type` has one way to look (`media` a gallery, `records` a card per
 * record, `qaList` numbered questions, `groupedList` headed groups, `longText`
 * markdown); the backend has already decided who may read which block.
 */
export function AudienceSections({
  sections,
  variant = "open",
  emptyMessage,
}: {
  sections: AudienceSection[];
  variant?: SectionsVariant;
  emptyMessage?: string;
}) {
  if (sections.length === 0) {
    return emptyMessage ? <p className="text-osce-body text-b2c-text-muted">{emptyMessage}</p> : null;
  }
  if (variant === "brief") return <BriefSections sections={sections} />;
  if (variant === "tabs" && sections.length > 1) return <SectionTabs sections={sections} />;

  return (
    <>
      {sections.map((section) =>
        variant === "collapsible" ? (
          <Dropdown key={section.id} title={section.title} className="mt-0" defaultOpen>
            <SectionBlocks section={section} />
          </Dropdown>
        ) : (
          <DoctorInfoSection key={section.id} title={section.title}>
            <SectionBlocks section={section} />
          </DoctorInfoSection>
        ),
      )}
    </>
  );
}

/**
 * The candidate's reading, matching the legacy b2c doctor screens: sections
 * flattened, each block a `DoctorInfoSection` with the icon, badge tone and
 * heading its block id had there, in the legacy reading order.
 */
function BriefSections({ sections }: { sections: AudienceSection[] }) {
  return (
    <>
      {briefBlockEntries(sections).map(({ block, title, icon, tone }) => (
        <DoctorInfoSection key={block.id} title={title} icon={icon} iconTone={tone}>
          <BlockView block={block} />
        </DoctorInfoSection>
      ))}
    </>
  );
}

function SectionTabs({ sections }: { sections: AudienceSection[] }) {
  const [active, setActive] = useState(sections[0]!.id);
  const current = sections.find((section) => section.id === active) ?? sections[0]!;
  return (
    <div className="space-y-4">
      <B2CSegmentedTabs
        aria-label="Sections"
        items={sections.map((section) => ({ id: section.id, label: section.title }))}
        value={current.id}
        onChange={setActive}
      />
      <DoctorInfoSection title={current.title}>
        <SectionBlocks section={current} />
      </DoctorInfoSection>
    </div>
  );
}

function SectionBlocks({ section }: { section: AudienceSection }) {
  return (
    <div className="space-y-4">
      {section.blocks.map((block) => (
        <div key={block.id}>
          {block.label ? (
            <p className="mb-1 text-osce-body font-medium text-b2c-text-secondary">{block.label}</p>
          ) : null}
          <BlockView block={block} />
        </div>
      ))}
    </div>
  );
}

/** One block, drawn the way its type says; a value in an unexpected shape falls back to text. */
export function BlockView({ block }: { block: AudienceBlock }) {
  const { value } = block;
  switch (block.type) {
    case "media": {
      const items = mediaItems(value);
      if (items.length > 0) return <MediaGallery items={items} />;
      break;
    }
    case "records":
      if (Array.isArray(value) && value.every(isRecord)) {
        return <RecordCards records={value} fields={block.fields ?? null} />;
      }
      break;
    case "qaList":
      if (Array.isArray(value) && value.every(isRecord)) return <QaList pairs={value} />;
      break;
    case "groupedList":
      if (isRecord(value)) return <GroupedList groups={value} />;
      break;
    case "longText":
      if (typeof value === "string") return <MarkdownRenderer content={value} />;
      break;
  }
  const items = Array.isArray(value) ? value.map(asText).filter(Boolean) : null;
  if (items && items.length > 0) return <DoctorInfoBulletList items={items} />;
  return <p className="whitespace-pre-wrap">{asText(value)}</p>;
}

/**
 * A media block: images in a grid, click to enlarge; audio and video with the
 * browser's own controls; a PDF as a link. A plain `<img>` rather than
 * `next/image`: these are absolute URLs on hosts this app does not configure,
 * and an unconfigured host is a runtime error rather than a slow image.
 */
function MediaGallery({ items }: { items: MediaItem[] }) {
  const [enlarged, setEnlarged] = useState<MediaItem | null>(null);
  const images = items.filter((item) => item.kind === "image");
  const others = items.filter((item) => item.kind !== "image");
  return (
    <div className="space-y-3">
      {images.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {images.map((item, index) => (
            <figure key={item.url}>
              <button type="button" className="group block w-full text-left" onClick={() => setEnlarged(item)}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.url}
                  alt={item.alt ?? item.caption ?? `Clinical material ${index + 1}`}
                  className="h-40 w-full rounded-md border border-b2c-border object-cover transition-transform duration-300 group-hover:scale-[1.01]"
                />
              </button>
              {item.caption ? (
                <figcaption className="mt-1 text-osce-caption text-b2c-text-muted">{item.caption}</figcaption>
              ) : null}
            </figure>
          ))}
        </div>
      ) : null}
      {images.length > 0 ? (
        <p className="text-center text-osce-body text-b2c-text-muted">Click to enlarge</p>
      ) : null}
      {others.map((item) => (
        <figure key={item.url} className="rounded-osce-md border border-b2c-border bg-osce-surface p-3">
          {/* Authored clinical media carries no caption track; its caption is shown beneath. */}
          {item.kind === "audio" ? (
            // eslint-disable-next-line jsx-a11y/media-has-caption
            <audio controls preload="metadata" src={item.url} className="w-full" />
          ) : item.kind === "video" ? (
            // eslint-disable-next-line jsx-a11y/media-has-caption
            <video controls preload="metadata" src={item.url} className="w-full rounded-md" />
          ) : (
            <a href={item.url} target="_blank" rel="noreferrer" className="font-medium text-osce-accent hover:underline">
              {item.caption ?? "Open document"}
            </a>
          )}
          {item.caption && item.kind !== "pdf" ? (
            <figcaption className="mt-2 text-osce-caption text-b2c-text-muted">{item.caption}</figcaption>
          ) : null}
        </figure>
      ))}
      {enlarged && (
        <Modal onClose={() => setEnlarged(null)} width="min(95vw, 56rem)" height="fit-content">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={enlarged.url} alt={enlarged.alt ?? enlarged.caption ?? "Enlarged"} className="h-auto w-full rounded-md" />
        </Modal>
      )}
    </div>
  );
}

/** One hairline card per record, its fields in the template's order (or the data's). */
function RecordCards({
  records,
  fields,
}: {
  records: Record<string, unknown>[];
  fields: { key: string; label: string }[] | null;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
      {records.map((record, index) => {
        const columns = fields ?? Object.keys(record).map((key) => ({ key, label: humanise(key) }));
        return (
          <div key={index} className="rounded-osce-md border border-b2c-border bg-osce-surface p-4">
            <dl className="space-y-2">
              {columns.map(({ key, label }) => {
                const cell = record[key];
                if (Array.isArray(cell) ? cell.length === 0 : !asText(cell)) return null;
                return (
                  <div key={key}>
                    <dt className="text-osce-caption font-medium uppercase tracking-wide text-b2c-text-muted">
                      {label}
                    </dt>
                    <dd className="text-osce-body text-b2c-text">
                      {Array.isArray(cell) ? (
                        <DoctorInfoBulletList items={cell.map(asText).filter(Boolean)} />
                      ) : (
                        asText(cell)
                      )}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </div>
        );
      })}
    </div>
  );
}

/** Numbered questions, each with its answer beneath. */
function QaList({ pairs }: { pairs: Record<string, unknown>[] }) {
  return (
    <ol className="space-y-3">
      {pairs.map((pair, index) => (
        <li key={index} className="rounded-osce-md border border-b2c-border bg-osce-surface p-4">
          <p className="font-medium text-b2c-text">
            {index + 1}. {asText(pair.question)}
          </p>
          {asText(pair.answer) ? (
            <p className="mt-2 whitespace-pre-wrap text-b2c-text-secondary">{asText(pair.answer)}</p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

/** A heading per group; each item is text or a `{title, reasons[]}` with sub-bullets. */
function GroupedList({ groups }: { groups: Record<string, unknown> }) {
  return (
    <div className="space-y-4">
      {Object.entries(groups).map(([group, items]) => (
        <div key={group}>
          <p className="mb-2 font-medium text-b2c-text">{humanise(group)}</p>
          <ol className="list-decimal space-y-2 pl-5 marker:text-b2c-text-muted">
            {(Array.isArray(items) ? items : [items]).map((item, index) =>
              isRecord(item) ? (
                <li key={index}>
                  <span className="text-b2c-text">{asText(item.title)}</span>
                  {Array.isArray(item.reasons) && item.reasons.length > 0 ? (
                    <DoctorInfoBulletList items={item.reasons.map(asText).filter(Boolean)} className="mt-1" />
                  ) : null}
                </li>
              ) : (
                <li key={index} className="text-b2c-text">
                  {asText(item)}
                </li>
              ),
            )}
          </ol>
        </div>
      ))}
    </div>
  );
}
