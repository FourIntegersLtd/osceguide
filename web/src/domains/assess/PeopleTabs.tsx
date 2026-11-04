"use client";

import { useRouter } from "next/navigation";
import { B2CSegmentedTabs } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { useAssessWords } from "@/domains/assess/useAssessWords";

type PeopleTab = "trainees" | "team";

/**
 * Trainees and Team are one place in the menu (People). The bar shows only for
 * someone who may open both, so a supervisor sees the trainees and no tabs.
 */
export function PeopleTabs({ active }: { active: PeopleTab }) {
  const w = useAssessWords();
  const router = useRouter();
  const { hrefFor } = useSurface();
  const { session } = useSession();
  if (!can(session, "manage_team")) return null;
  return (
    <B2CSegmentedTabs<PeopleTab>
      items={[
        { id: "trainees", label: w.Trainees },
        { id: "team", label: "Team" },
      ]}
      value={active}
      onChange={(id) => router.push(hrefFor(`/${id}`))}
      aria-label={w.People}
    />
  );
}
