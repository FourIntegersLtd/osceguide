"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AsyncBoundary, B2CPageHeader, B2CSegmentedTabs, ButtonLink } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { B2CSegmentedTabItem } from "@/foundation/ui";
import { useCurrentExam, showsMarkingTips } from "@/foundation/session";
import TipContent from "@/capabilities/station-runner/tips/TipContent";
import { CombineStations } from "@/domains/train/mocks/CombineStations";
import { FlaggedStations } from "@/domains/train/mocks/FlaggedStations";
import { MockSetup } from "@/domains/train/mocks/MockSetup";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { useMockWorkspace } from "@/domains/train/mocks/useMockWorkspace";

type MockTab = "setup" | "flagged" | "combine" | "tips";

const MOCK_TABS: readonly MockTab[] = ["setup", "flagged", "combine", "tips"];

function tabFromParam(value: string | null): MockTab {
  return MOCK_TABS.find((tab) => tab === value) ?? "setup";
}

/**
 * AI Practice: build a session, combine stations, or pick up a flagged one.
 *
 * The retiring client's `MockCore`, tab for tab: its order, its icons, and the
 * `?tab=` in the address so a refresh or a shared link lands on the same tab.
 * Consultation Tips is the SCA toolkit a candidate reads before they start, so
 * like the old client it is offered to SCA candidates only. The sessions list
 * is its own route, `/mocks/list`, reached from "View All Sessions".
 */
export function Mocks() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<MockTab>(tabFromParam(searchParams.get("tab")));
  const workspace = useMockWorkspace();
  const { settings } = useCurrentExam();
  const { hrefFor } = useSurface();

  const handleTabChange = (tab: MockTab) => {
    setActiveTab(tab);
    router.push(`?tab=${tab}`);
  };

  // Canvas order: setup, tips (SCA only), combine, flagged. Sentence case, no icons.
  const items: B2CSegmentedTabItem<MockTab>[] = [
    { id: "setup", label: "Setup" },
    ...(showsMarkingTips(settings) ? [{ id: "tips" as const, label: "Consultation tips" }] : []),
    { id: "combine", label: "Combine stations" },
    { id: "flagged", label: "Flagged stations" },
  ];

  return (
    <div className="w-full">
      <B2CPageHeader
        title="Practice"
        action={
          <ButtonLink href={hrefFor("/mocks/list")} variant="secondary" size="md">
            View all sessions
          </ButtonLink>
        }
      />

      <B2CSegmentedTabs
        className="mb-6"
        items={items}
        value={activeTab}
        onChange={handleTabChange}
        aria-label="AI Practice"
      />

      <div className="w-full">
        {activeTab === "flagged" ? (
          // Its own request: what somebody reported is not part of the
          // workspace listing, and mounting it inside the boundary below would
          // make a failure to read their reports look like an empty account.
          <FlaggedStations />
        ) : activeTab === "tips" ? (
          <div className="space-y-6">
            <B2CHero eyebrow="Consultation tips" title="One consultation skill at a time">
              A skill from the RCGP SCA Consultation Toolkit, with exercises to try in your next station.
            </B2CHero>
            <TipContent />
          </div>
        ) : (
          <AsyncBoundary state={workspace}>
            {(data) =>
              activeTab === "combine" ? (
                <CombineStations workspace={data} />
              ) : (
                <MockSetup workspace={data} onCreated={workspace.reload} />
              )
            }
          </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
