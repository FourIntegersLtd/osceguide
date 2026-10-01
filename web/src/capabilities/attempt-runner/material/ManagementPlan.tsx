"use client";

import { HiOutlineClipboardDocumentList, HiOutlineUser } from "react-icons/hi2";
import type { AttemptReview } from "@/capabilities/attempt-runner/api";
import { StationComments } from "@/capabilities/community/StationComments";
import { Dropdown } from "@/foundation/table";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CSectionIconBadge,
  MarkdownRenderer,
  cn,
} from "@/foundation/ui";
import { b2cPageTitle, b2cReadingTones, b2cSectionTitle } from "@/foundation/ui/productTokens";
import { AudienceSections, BlockView, sectionsFor } from "./AudienceSections";
import { managementLayout, type ManagementEntry } from "./managementBlockMeta";
import { prepareListItem } from "./managementListHelpers";
import { asText } from "./sectionsByAudience";

/**
 * The model answer once the consultation is over, laid out as the legacy b2c
 * management screen: a "Patient information" card holding the candidate's
 * brief, then a "Management plan" card whose blocks are tone-coloured cards
 * grouped by consultation stage (`managementBlockMeta`).
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
    <div className="max-w-full select-none space-y-6 overflow-x-hidden sm:space-y-8">
      <h1 className={`${b2cPageTitle} my-4 text-center sm:my-6`}>{review.station_title}</h1>

      {briefSections.length > 0 ? (
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>
            <B2CSectionIconBadge tone="emerald" size="sm">
              <HiOutlineUser aria-hidden />
            </B2CSectionIconBadge>
            Patient information
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
            <AudienceSections sections={briefSections} variant="brief" />
          </B2CPanelCardBody>
        </B2CPanelCard>
      ) : null}

      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <B2CSectionIconBadge tone="primary" size="sm">
            <HiOutlineClipboardDocumentList aria-hidden />
          </B2CSectionIconBadge>
          Management plan
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-4">
          {!hasModelAnswer ? (
            <p className="text-osce-body text-b2c-text-muted">There is no model answer for this station.</p>
          ) : null}

          {layout.lead.map((entry) => (
            <ToneCard key={entry.block.id} entry={entry} />
          ))}

          {layout.groups.map((group) =>
            group.collapsible ? (
              <Dropdown key={group.title} title={group.title} className="mt-0">
                <ToneCardGrid entries={group.entries} />
              </Dropdown>
            ) : (
              <section key={group.title} className="my-6 space-y-4 sm:my-8 sm:space-y-6">
                <h3 className={`${b2cSectionTitle} border-b border-b2c-border pb-2`}>{group.title}</h3>
                <ToneCardGrid entries={group.entries} />
              </section>
            ),
          )}
        </B2CPanelCardBody>
      </B2CPanelCard>

      <StationComments stationId={review.station_id} />
    </div>
  );
}

/** A group's cards: one column, two on a very wide screen, as the legacy grid. */
function ToneCardGrid({ entries }: { entries: ManagementEntry[] }) {
  return (
    <div className={cn("grid grid-cols-1 gap-6", entries.length > 1 && "2xl:grid-cols-2")}>
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
    <div className={cn("rounded-2xl border p-4", tone.card)}>
      <h4 className={cn("mb-2 text-osce-body font-medium", tone.title)}>{entry.title}</h4>
      {listItems ? (
        <ul className={cn("list-disc p-2 pl-5 text-osce-body [list-style-position:outside] lg:p-4", tone.list)}>
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
    </div>
  );
}
