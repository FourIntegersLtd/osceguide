"use client";

import { HiOutlineUser } from "react-icons/hi2";
import { B2CSectionIconBadge } from "@/foundation/ui/B2CSectionIconBadge";
import { b2cGroupedRowSubtitle, b2cSectionTitle } from "@/foundation/ui/productTokens";
import {
  AudienceSections,
  sectionsFor,
  type AudienceSection,
} from "@/capabilities/attempt-runner/material/AudienceSections";

/** The actor's script: the patient audience of the station's template, one tab per section. */
export function PatientRoleplayScript({
  sections,
  subtitle,
  noBorder = false,
}: {
  sections: AudienceSection[];
  subtitle?: string | null;
  noBorder?: boolean;
}) {
  return (
    <div
      className={`flex h-full flex-col overflow-hidden bg-osce-surface text-osce-body ${noBorder ? "" : "rounded-osce-lg border border-b2c-border"}`}
    >
      <div className="flex shrink-0 items-center gap-2.5 px-4 pt-4 sm:px-5">
        <B2CSectionIconBadge tone="violet">
          <HiOutlineUser aria-hidden />
        </B2CSectionIconBadge>
        <div className="min-w-0">
          <h3 className={b2cSectionTitle}>Patient roleplay script</h3>
          <p className={`${b2cGroupedRowSubtitle} truncate`}>{subtitle || "Standard patient"}</p>
        </div>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
        <AudienceSections
          sections={sectionsFor(sections, "patient")}
          variant="tabs"
          emptyMessage="There is no patient script for this station."
        />
      </div>
    </div>
  );
}
