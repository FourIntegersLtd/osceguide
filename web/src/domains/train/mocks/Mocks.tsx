"use client";

import { useState } from "react";
import { AsyncBoundary, B2CPageHeader, B2CSegmentedTabs } from "@/foundation/ui";
import type { B2CSegmentedTabItem } from "@/foundation/ui";
import { CombineStations } from "@/domains/train/mocks/CombineStations";
import { MockSessions } from "@/domains/train/mocks/MockSessions";
import { MockSetup } from "@/domains/train/mocks/MockSetup";
import { useMockWorkspace } from "@/domains/train/mocks/useMockWorkspace";

type MockTab = "setup" | "combine" | "sessions";

const TABS: B2CSegmentedTabItem<MockTab>[] = [
  { id: "setup", label: "Setup" },
  { id: "combine", label: "Combine Stations" },
  { id: "sessions", label: "Your Sessions" },
];

/**
 * AI Practice: build a session, or pick up one you have.
 *
 * The retiring client split this over two routes — `/mocks` for the tabs and
 * `/mocks/list` for the sessions — and then put a "View All Sessions" button
 * on the form to get between them. There is one route here and the list is the
 * third tab, so the thing somebody came for is one tap away rather than one
 * navigation.
 *
 * Its two absent tabs are other people's work, not gaps: "Consultation Tips"
 * belongs to the help capability and "Flagged Stations" to the station
 * library. Both mount themselves when those land.
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
              <MockSessions workspace={data} />
            )
          }
        </AsyncBoundary>
      </div>
    </div>
  );
}
