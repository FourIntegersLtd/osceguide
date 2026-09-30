"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  HiOutlineCog6Tooth,
  HiOutlineFlag,
  HiOutlineSquare3Stack3D,
} from "react-icons/hi2";
import { PiSparkle } from "react-icons/pi";
import { RiSpeakLine } from "react-icons/ri";
import { AsyncBoundary, B2CPageHeader, B2CSegmentedTabs } from "@/foundation/ui";
import type { B2CSegmentedTabItem } from "@/foundation/ui";
import { useCurrentExam, showsMarkingTips } from "@/foundation/session";
import TipContent from "@/capabilities/station-runner/tips/TipContent";
import { CombineStations } from "@/domains/train/mocks/CombineStations";
import { FlaggedStations } from "@/domains/train/mocks/FlaggedStations";
import { MockSetup } from "@/domains/train/mocks/MockSetup";
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

  const handleTabChange = (tab: MockTab) => {
    setActiveTab(tab);
    router.push(`?tab=${tab}`);
  };

  const items: B2CSegmentedTabItem<MockTab>[] = [
    {
      id: "setup",
      label: (
        <span className="inline-flex items-center gap-1.5">
          <HiOutlineCog6Tooth className="h-4 w-4" aria-hidden />
          Setup
        </span>
      ),
    },
  ];
  if (showsMarkingTips(settings)) {
    items.push({
      id: "tips",
      label: (
        <span className="inline-flex items-center gap-1.5">
          Consultation Tips
          <PiSparkle className="h-4 w-4 text-inherit animate-bounce" />
        </span>
      ),
    });
  }
  items.push(
    {
      id: "combine",
      label: (
        <span className="inline-flex items-center gap-1.5">
          <HiOutlineSquare3Stack3D className="h-4 w-4" aria-hidden />
          Combine Stations
        </span>
      ),
    },
    {
      id: "flagged",
      label: (
        <span className="inline-flex items-center gap-1.5">
          <HiOutlineFlag className="h-4 w-4" aria-hidden />
          Flagged Stations
        </span>
      ),
    },
  );

  return (
    <div className="w-full">
      <B2CPageHeader title="Practice" icon={RiSpeakLine} />

      <B2CSegmentedTabs
        className="mb-4 sm:mb-6"
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
          <TipContent width="w-3/5" />
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
