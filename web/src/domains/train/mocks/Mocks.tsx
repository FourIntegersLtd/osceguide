"use client";

import { useState } from "react";
import { AsyncBoundary, B2CPageHeader, B2CSegmentedTabs } from "@/foundation/ui";
import type { B2CSegmentedTabItem } from "@/foundation/ui";
import TipContent from "@/capabilities/station-runner/tips/TipContent";
import { CombineStations } from "@/domains/train/mocks/CombineStations";
import { FlaggedStations } from "@/domains/train/mocks/FlaggedStations";
import { MockSessions } from "@/domains/train/mocks/MockSessions";
import { MockSetup } from "@/domains/train/mocks/MockSetup";
import { useMockWorkspace } from "@/domains/train/mocks/useMockWorkspace";

type MockTab = "setup" | "combine" | "flagged" | "sessions" | "tips";

const TABS: B2CSegmentedTabItem<MockTab>[] = [
  { id: "setup", label: "Setup" },
  { id: "combine", label: "Combine Stations" },
  { id: "flagged", label: "Flagged Stations" },
  { id: "tips", label: "Consultation Tips" },
  { id: "sessions", label: "Your Sessions" },
];

/**
 * AI Practice: build a session, or pick up one you have.
 *
 * The retiring client split this over two routes — `/mocks` for the tabs and
 * `/mocks/list` for the sessions — and then put a "View All Sessions" button
 * on the form to get between them. There is one route here and the list is the
 * last tab, so the thing somebody came for is one tap away rather than one
 * navigation.
 *
 * The retiring client's four tabs, in its order, plus the sessions list that
 * used to be a second route. Consultation Tips is the toolkit a candidate
 * reads before they start, not only the one inside a marking modal.
 */
export function Mocks() {
  const [activeTab, setActiveTab] = useState<MockTab>("setup");
  const workspace = useMockWorkspace();

  return (
    <div className="w-full">
      <B2CPageHeader title="Practice" />

      <B2CSegmentedTabs
        items={TABS}
        value={activeTab}
        onChange={setActiveTab}
        aria-label="AI Practice"
      />

      <div className="w-full">
        {activeTab === "tips" ? (
          <TipContent />
        ) : activeTab === "flagged" ? (
          // Its own request: what somebody reported is not part of the
          // workspace listing, and mounting it inside the boundary above would
          // make a failure to read their reports look like an empty account.
          <FlaggedStations />
        ) : (
          <AsyncBoundary state={workspace}>
            {(data) =>
              activeTab === "setup" ? (
                <MockSetup
                  workspace={data}
                  onCreated={workspace.reload}
                  onViewSessions={() => setActiveTab("sessions")}
                />
              ) : activeTab === "combine" ? (
                <CombineStations workspace={data} onCreated={workspace.reload} />
              ) : (
                <MockSessions workspace={data} onChanged={workspace.reload} />
              )
            }
          </AsyncBoundary>
        )}
      </div>
    </div>
  );
}
