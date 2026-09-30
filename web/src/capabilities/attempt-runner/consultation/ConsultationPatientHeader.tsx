"use client";

import { cn, productTokens } from "@/foundation/ui";
import type { ConsultationPatient } from "@/capabilities/attempt-runner/consultation/patientIdentity";

const { b2cBodyTextMuted, b2cGroupedRowTitle } = productTokens;

/**
 * Compact patient row kept visible for the whole call — legacy
 * `ConsultationPatientHeader`.
 */
export function ConsultationPatientHeader({
  patient,
  className,
}: {
  patient: ConsultationPatient;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-center gap-2.5", className)}>
      <span
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-osce-accent-subtle bg-osce-accent-subtle text-sm font-semibold text-osce-accent"
        aria-hidden
      >
        {patient.initials}
      </span>
      <div className="min-w-0 text-left">
        <p className={cn(b2cGroupedRowTitle, "truncate font-semibold")}>{patient.name}</p>
        {patient.detail ? (
          <p className={cn(b2cBodyTextMuted, "truncate")}>{patient.detail}</p>
        ) : null}
      </div>
    </div>
  );
}
