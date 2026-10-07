"use client";

import { useState } from "react";
import { B2CPageHeader } from "@/foundation/ui";
import { ProgrammesSection } from "@/capabilities/authoring";
import { PlatformExams } from "@/domains/assess/programmes/PlatformExams";

/**
 * The organisation's programmes: one per exam it runs sittings against.
 *
 * An exam the platform publishes is adopted from the list on top; the list
 * below is the same as Authoring → Programmes (create by exam, activate,
 * retire), because that is all `/orgs/{slug}/programmes` holds. The richer
 * programme (purpose, dates, lead, people) waits on an API that does not exist
 * yet, so it is not shown here.
 */
export function Programmes({ orgSlug }: { orgSlug: string }) {
  const [adopted, setAdopted] = useState(0);
  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Programmes"
        subtitle="A programme is an exam you run sittings against. Adopt one the platform publishes or add your own, activate it, and it is offered when you schedule a sitting."
      />
      <PlatformExams orgSlug={orgSlug} onAdopted={() => setAdopted((n) => n + 1)} />
      <ProgrammesSection key={adopted} />
    </div>
  );
}
