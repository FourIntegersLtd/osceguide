"use client";

import { Suspense, useEffect, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  B2CPageHeader,
  B2CSegmentedTabs,
  type B2CSegmentedTabItem,
  LeaveConfirmModal,
  PlatformTabbedScreen,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import ProfilePanel from "@/capabilities/account/settings/ProfilePanel";
import { arrangeTabs, tabsFor, type SettingsTab } from "@/capabilities/account/settings/settingsTabs";

export type { SettingsTab };
import PreferencesPanel from "@/capabilities/account/settings/PreferencesPanel";
import PaymentsPanel from "@/capabilities/account/settings/PaymentsPanel";
import ReferralsPanel from "@/capabilities/account/settings/ReferralsPanel";

/** A tab an arm adds beside the account's own. */
export interface ExtraSettingsTab {
  id: string;
  label: string;
  /** A panel that can hold unsaved edits takes the setter that arms the leave guard. */
  panel: (setDirty: (dirty: boolean) => void) => ReactNode;
  /** Placed after the person's own tabs instead of before them. */
  after?: boolean;
}

const NO_EXTRA_TABS: ExtraSettingsTab[] = [];


const firstTabFor = (surface: string): SettingsTab => (surface === "platform" ? "account" : "profile");

/** Organisation admins open on their organisation; everyone else on their own first tab. */
const openingTab = (surface: string, extraTabs: ExtraSettingsTab[]): string =>
  extraTabs.some((entry) => entry.id === "organisation") ? "organisation" : firstTabFor(surface);

/**
 * The person, on whichever arm they are standing.
 *
 * Mounted on all five surfaces deliberately. The retiring client had settings
 * under the consumer arm only, which meant an institution's supervisor — the
 * person who signs off results — could not change their own password. Nothing
 * on this screen is consumer-specific: everybody has a name, a password, the
 * access they were granted or bought, and a tutor keeping notes on them.
 *
 * `extraTabs` is how an arm adds tabs of its own (an institution's
 * organisation and sign-in panels) without this capability knowing the arm.
 */
export function Settings({ extraTabs = NO_EXTRA_TABS }: { extraTabs?: ExtraSettingsTab[] }) {
  const { surface } = useSurface();
  return (
    <Suspense
      fallback={<SettingsFrame tab={openingTab(surface, extraTabs)} onChange={() => {}} extraTabs={extraTabs} />}
    >
      <SettingsTabs extraTabs={extraTabs} />
    </Suspense>
  );
}

function SettingsTabs({ extraTabs }: { extraTabs: ExtraSettingsTab[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { surface } = useSurface();
  const tabs = tabsFor(surface);
  const requested = searchParams.get("tab");
  const [fallback, setFallback] = useState<string>(openingTab(surface, extraTabs));
  const known =
    tabs.some((entry) => entry.id === requested) ||
    extraTabs.some((entry) => entry.id === requested);
  const tab = requested !== null && known ? requested : fallback;

  /*
   * The query string is the source of truth when it names a tab, so a link to
   * "?tab=payments" — the one the cancelled-checkout page sends people back
   * to — opens on the right panel. State only fills in before anybody has
   * chosen, which keeps the two from disagreeing on a back navigation.
   */
  const handleChange = (next: string) => {
    setFallback(next);
    router.push(`?tab=${next}`, { scroll: false });
  };

  return <SettingsFrame tab={tab} onChange={handleChange} extraTabs={extraTabs} />;
}

function SettingsFrame({
  tab,
  onChange,
  extraTabs,
}: {
  tab: string;
  onChange: (tab: string) => void;
  extraTabs: ExtraSettingsTab[];
}) {
  const { surface } = useSurface();
  // The old screen's unsaved-changes guard: an edited, unsaved username stops
  // a tab switch (and a page unload) until the person says so.
  const [isDirty, setDirty] = useState(false);
  const [pendingTab, setPendingTab] = useState<string | null>(null);

  useEffect(() => {
    if (!isDirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const handleTabChange = (next: string) => {
    if (next === tab) return;
    if (isDirty) {
      setPendingTab(next);
      return;
    }
    onChange(next);
  };

  const confirmLeaveTab = () => {
    const next = pendingTab;
    setPendingTab(null);
    setDirty(false);
    if (next) onChange(next);
  };

  const items: B2CSegmentedTabItem<string>[] = arrangeTabs(tabsFor(surface), extraTabs);

  const panels = (
    <>
      {tab === "profile" ? <ProfilePanel onDirtyChange={setDirty} /> : null}
      {tab === "account" || tab === "security" || tab === "data" ? (
        <ProfilePanel key={tab} part={tab} onDirtyChange={setDirty} />
      ) : null}
      {tab === "preferences" ? <PreferencesPanel /> : null}
      {tab === "payments" ? <PaymentsPanel /> : null}
      {tab === "referrals" ? <ReferralsPanel /> : null}
      {extraTabs.map((entry) => (tab === entry.id ? <div key={entry.id}>{entry.panel(setDirty)}</div> : null))}
    </>
  );

  const leaveModal = (
    <LeaveConfirmModal
      isOpen={pendingTab !== null}
      onStay={() => setPendingTab(null)}
      onLeave={confirmLeaveTab}
    />
  );

  if (surface === "platform") {
    return (
      <PlatformTabbedScreen
        title="Settings"
        description="Your own account: profile, sign-in and your data"
        tabs={items}
        value={tab}
        onChange={handleTabChange}
        ariaLabel="Settings"
      >
        {panels}
        {leaveModal}
      </PlatformTabbedScreen>
    );
  }

  return (
    // The consumer screen is one 960px column (canvas `train-settings`); an
    // institution's extra tabs hold tables and keep the full width.
    <div className={surface === "train" ? "w-full max-w-[960px]" : undefined}>
      <B2CPageHeader title="Settings" />
      <B2CSegmentedTabs
        className="mb-6"
        items={items}
        value={tab}
        onChange={handleTabChange}
        aria-label="Settings"
      />
      <div>{panels}</div>
      {leaveModal}
    </div>
  );
}
