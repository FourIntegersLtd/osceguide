"use client";

import type { AttemptReview } from "@/capabilities/attempt-runner/api";
import { StationComments } from "@/capabilities/community/StationComments";
import { Dropdown } from "@/foundation/table";
import { Card, MarkdownRenderer, cn } from "@/foundation/ui";
import { b2cReadingTones } from "@/foundation/ui/productTokens";
import { AudienceSections, BlockView, sectionsFor } from "./AudienceSections";
import { managementLayout, type ManagementEntry } from "./managementBlockMeta";
import { prepareListItem } from "./managementListHelpers";
import { asText } from "./sectionsByAudience";
import { B2CHero } from "@/foundation/ui/B2CHero";

/**
 * The model answer once the consultation is over: a "Model answer" hero, the
 * blocks as stage-coloured cards grouped by consultation stage
 * (`managementBlockMeta`), then the candidate's brief for reference.
 */
export function ManagementPlan({
  review,
}: {
  review: Pick<AttemptReview, "station_title" | "station_id" | "sections">;
}) {
  const briefSections = sectionsFor(review.sections, "candidate");
  const layout = managementLayout(sectionsFor(review.sections, "examiner"));
  const hasModelAnswer = layout.lead.length > 0 || layout.groups.length > 0;

  return (
    <div className="max-w-full select-none space-y-6 overflow-x-hidden">
      <B2CHero eyebrow="Model answer" title={review.station_title}>
        What a competent plan covers. Compare it with your transcript.
      </B2CHero>

      {!hasModelAnswer ? (
        <p className="text-osce-body text-b2c-text-muted">There is no model answer for this station.</p>
      ) : null}

      {layout.lead.length > 0 ? <ToneCardGrid entries={layout.lead} /> : null}

      {layout.groups.map((group) =>
        group.collapsible ? (
          <Dropdown key={group.title} title={group.title} className="mt-0">
            <ToneCardGrid entries={group.entries} />
          </Dropdown>
        ) : (
          <section key={group.title} className="space-y-3">
            <h3 className="text-osce-subheading font-semibold text-osce-ink-900">{group.title}</h3>
            <ToneCardGrid entries={group.entries} />
          </section>
        ),
      )}

      {briefSections.length > 0 ? (
        <Card title="Patient information">
          <div className="space-y-4">
            <AudienceSections sections={briefSections} variant="brief" />
          </div>
        </Card>
      ) : null}

      <StationComments stationId={review.station_id} />
    </div>
  );
}

/** A group's cards, two to a row from a tablet up. */
function ToneCardGrid({ entries }: { entries: ManagementEntry[] }) {
  return (
    <div className={cn("grid grid-cols-1 gap-3", entries.length > 1 && "md:grid-cols-2")}>
      {entries.map((entry) => (
        <ToneCard key={entry.block.id} entry={entry} />
      ))}
    </div>
  );
}

/**
 * One block as the legacy `InfoCard`: a rounded card in its stage's tone, the
 * heading in the tone's ink, a list as disc bullets with numbered lines as
 * bold sub-headings. Block types with their own shape (records, questions,
 * media) keep it inside the card.
 */
function ToneCard({ entry }: { entry: ManagementEntry }) {
  const tone = b2cReadingTones[entry.tone];
  const { block } = entry;
  const listItems = Array.isArray(block.value) && block.type === "list" ? block.value.map(asText).filter(Boolean) : null;

  return (
    <article className={cn("rounded-osce-lg border p-5", tone.card)}>
      <h4 className={cn("mb-2 text-osce-body font-semibold", tone.title)}>{entry.title}</h4>
      {listItems ? (
        <ul className={cn("list-disc space-y-1 pl-5 text-osce-meta leading-relaxed [list-style-position:outside]", tone.list)}>
          {listItems.map((item, index) => {
            const { text, isNumberedHeading } = prepareListItem(item);
            return (
              <li
                key={index}
                className={
                  isNumberedHeading
                    ? "mt-3 list-none whitespace-pre-wrap break-words font-semibold first:mt-0"
                    : "whitespace-pre-wrap break-words"
                }
              >
                {text}
              </li>
            );
          })}
        </ul>
      ) : typeof block.value === "string" ? (
        <div className={cn("text-osce-body leading-relaxed", tone.body)}>
          <MarkdownRenderer content={block.value} />
        </div>
      ) : (
        <div className={cn("text-osce-body", tone.body)}>
          <BlockView block={block} />
        </div>
      )}
    </article>
  );
}
