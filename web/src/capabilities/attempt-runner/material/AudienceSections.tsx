"use client";

import { useState } from "react";
import { Dropdown } from "@/foundation/table";
import { MarkdownRenderer, Modal } from "@/foundation/ui";
import { B2CSegmentedTabs } from "@/foundation/ui/B2CSegmentedTabs";
import { DoctorInfoBulletList, DoctorInfoSection } from "./DoctorInfoLayout";
import { asText, humanise, isRecord, type AudienceBlock, type AudienceSection } from "./sectionsByAudience";

export type { Audience, AudienceBlock, AudienceSection } from "./sectionsByAudience";
export { sectionLines, sectionsFor } from "./sectionsByAudience";

/**
 * How a set of sections is laid out: open cards for a brief, collapsible
 * panels for an examiner's model answer, one tab per section for an actor's script.
 */
export type SectionsVariant = "open" | "collapsible" | "tabs";

/**
 * A station's content, drawn from its template's own sections and block types
 * rather than by field name or exam, so a new exam's layout is template data.
 * Each block `type` has one way to look (`image` a grid, `records` a card per
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
    case "image": {
      const urls = (Array.isArray(value) ? value : [value]).filter(
        (url): url is string => typeof url === "string" && url.trim() !== "",
      );
      if (urls.length > 0) return <ImageGrid urls={urls} />;
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
 * Images, click to enlarge. A plain `<img>` rather than `next/image`: these are
 * absolute URLs on hosts this app does not configure, and an unconfigured host
 * is a runtime error rather than a slow image.
 */
function ImageGrid({ urls }: { urls: string[] }) {
  const [enlarged, setEnlarged] = useState<string | null>(null);
  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {urls.map((url, index) => (
          <button key={url} type="button" className="group text-left" onClick={() => setEnlarged(url)}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt={`Clinical material ${index + 1}`}
              className="h-40 w-full rounded-md border border-b2c-border object-cover transition-transform duration-300 group-hover:scale-[1.01]"
            />
          </button>
        ))}
      </div>
      <p className="mt-2 text-center text-osce-body text-b2c-text-muted">Click to enlarge</p>
      {enlarged && (
        <Modal onClose={() => setEnlarged(null)} width="min(95vw, 56rem)" height="fit-content">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={enlarged} alt="Enlarged" className="h-auto w-full rounded-md" />
        </Modal>
      )}
    </>
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
