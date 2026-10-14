"use client";

import { useState } from "react";
import { HiOutlineUser } from "react-icons/hi2";
import { B2CSectionIconBadge, B2CSegmentedTabs } from "@/foundation/ui";
import { b2cGroupedRowSubtitle, b2cReadingTones, b2cSectionTitle } from "@/foundation/ui/productTokens";
import { BlockView, sectionsFor, type AudienceSection } from "@/capabilities/attempt-runner/material/AudienceSections";
import { DoctorInfoBulletList, DoctorInfoSection } from "@/capabilities/attempt-runner/material/DoctorInfoLayout";
import {
  patientScriptTabs,
  scriptLines,
  type PatientScriptEntry,
  type PatientScriptTab,
} from "@/capabilities/debrief/patientScriptMeta";

const TAB_ITEMS: Array<{ id: PatientScriptTab; label: string }> = [
  { id: "history", label: "History" },
  { id: "ice", label: "ICE & Concerns" },
  { id: "persona", label: "Persona" },
];

/**
 * The actor's script, as the legacy b2c `PatientPreparation`: a header, then
 * History / ICE & Concerns / Persona tabs, each a run of iconed sections
 * (`patientScriptMeta` says which block goes where).
 */
export function PatientRoleplayScript({
  sections,
  subtitle,
  noBorder = false,
}: {
  sections: AudienceSection[];
  subtitle?: string | null;
  noBorder?: boolean;
}) {
  const [activeTab, setActiveTab] = useState<PatientScriptTab>("history");
  const tabs = patientScriptTabs(sectionsFor(sections, "patient"));
  const hasScript = tabs.history.length + tabs.ice.length + tabs.persona.length > 0;

  return (
    <div
      className={`flex h-full flex-col overflow-hidden bg-osce-surface text-osce-body ${noBorder ? "" : "rounded-osce-lg border border-b2c-border"}`}
    >
      <div className="shrink-0 px-4 pt-4 sm:px-5">
        <div className="flex items-center gap-2.5">
          <B2CSectionIconBadge tone="violet">
            <HiOutlineUser aria-hidden />
          </B2CSectionIconBadge>
          <div className="min-w-0">
            <h3 className={b2cSectionTitle}>Patient roleplay script</h3>
            <p className={`${b2cGroupedRowSubtitle} truncate`}>{subtitle || "Standard patient"}</p>
          </div>
        </div>
        {hasScript ? (
          <B2CSegmentedTabs
            className="mt-3"
            aria-label="Patient script sections"
            items={TAB_ITEMS}
            value={activeTab}
            onChange={setActiveTab}
          />
        ) : null}
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
        {!hasScript ? (
          <p className="text-b2c-text-muted">There is no patient script for this station.</p>
        ) : null}
        {tabs[activeTab].map((entry) => (
          <ScriptSection key={entry.block.id} entry={entry} />
        ))}
        {hasScript && tabs[activeTab].length === 0 ? (
          <p className="text-b2c-text-muted">Nothing was written for this part of the script.</p>
        ) : null}
        {hasScript && activeTab === "persona" ? (
          <p className={`rounded-osce-md border px-3 py-2.5 ${b2cReadingTones.tip.card} ${b2cReadingTones.tip.body}`}>
            Respond naturally to the doctor&apos;s questions and share your thoughts, concerns, and
            expectations.
          </p>
        ) : null}
      </div>
    </div>
  );
}

/** One block of the script under its legacy heading, drawn by its style. */
function ScriptSection({ entry }: { entry: PatientScriptEntry }) {
  const { block } = entry;
  const isPlainText = typeof block.value === "string" || (Array.isArray(block.value) && block.type === "list");
  const lines = isPlainText ? scriptLines(block.value) : [];

  return (
    <DoctorInfoSection title={entry.title} icon={entry.icon} iconTone={entry.tone} emphasize={entry.style === "quote"}>
      {!isPlainText ? (
        <BlockView block={block} />
      ) : entry.style === "quote" ? (
        <p className="italic">&ldquo;{lines.join(" ")}&rdquo;</p>
      ) : entry.style === "questions" ? (
        <ul className="space-y-2">
          {lines.map((line, index) => (
            <li
              key={index}
              className={`rounded-osce-md border px-3 py-2.5 font-medium leading-snug ${b2cReadingTones.practice.card} ${b2cReadingTones.practice.body}`}
            >
              {line}
            </li>
          ))}
        </ul>
      ) : lines.length > 1 ? (
        <DoctorInfoBulletList items={lines} className="list-disc pl-5" />
      ) : (
        <p className="whitespace-pre-wrap">{lines[0]}</p>
      )}
    </DoctorInfoSection>
  );
}
