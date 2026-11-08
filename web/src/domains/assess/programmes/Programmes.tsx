"use client";

import { useState } from "react";
import { B2CPageHeader, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { ProgrammesSection } from "@/capabilities/authoring";
import { PlatformExams } from "@/domains/assess/programmes/PlatformExams";
import { useAssessWords } from "@/capabilities/assess-words";
import { programmesCopy } from "@/domains/assess/programmes/support";

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
  const copy = programmesCopy(useAssessWords());
  const [adopted, setAdopted] = useState(0);
  const { hrefFor } = useSurface();
  return (
    <div className="flex max-w-[1080px] flex-col gap-6" data-testid="programmes-page">
      <B2CPageHeader
        board
        action={<span aria-hidden />}
        className="!mb-0"
        wideSubtitle
        eyebrow="Organise"
        title={copy.title}
        back={{ href: hrefFor("/authoring") + "/exams", label: "Exams" }}
        subtitle={copy.subtitle}
      />
      <PlatformExams orgSlug={orgSlug} onAdopted={() => setAdopted((n) => n + 1)} />
      <div className="flex flex-col gap-6" data-testid="your-programmes">
        <h2 className={`m-0 ${b2bTokens.assessEyebrow}`}>{copy.yours}</h2>
        <ProgrammesSection key={adopted} />
      </div>
    </div>
  );
}
