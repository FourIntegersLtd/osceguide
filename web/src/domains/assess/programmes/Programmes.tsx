"use client";

import { B2CPageHeader } from "@/foundation/ui";
import { ProgrammesSection } from "@/capabilities/authoring";

/**
 * The organisation's programmes: one per exam it runs sittings against.
 *
 * This is the same list as Authoring → Programmes (create by exam, activate,
 * retire), because that is all `/orgs/{slug}/programmes` holds. The richer
 * programme (purpose, dates, lead, people) waits on an API that does not exist
 * yet, so it is not shown here.
 */
export function Programmes() {
  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Programmes"
        subtitle="A programme is an exam you run sittings against. Add one, activate it, and it is offered when you schedule a sitting."
      />
      <ProgrammesSection />
    </div>
  );
}
