"use client";

import { Suspense, useEffect, useState, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HiOutlineCog6Tooth } from "react-icons/hi2";
import {
  B2CPageHeader,
  B2CSegmentedTabs,
  type B2CSegmentedTabItem,
  LeaveConfirmModal,
  PlatformTabbedScreen,
} from "@/foundation/ui";
import { isPlatformAdmin, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import ProfilePanel from "@/capabilities/account/settings/ProfilePanel";
import PreferencesPanel from "@/capabilities/account/settings/PreferencesPanel";
import ExamPanel from "@/capabilities/account/settings/ExamPanel";
import PaymentsPanel from "@/capabilities/account/settings/PaymentsPanel";
import ReferralsPanel from "@/capabilities/account/settings/ReferralsPanel";
import TutorMemoryPanel from "@/capabilities/account/settings/TutorMemoryPanel";

export type SettingsTab = "profile" | "preferences" | "exam" | "payments" | "referrals" | "memory";

/** A tab an arm adds beside the account's own. */
export interface ExtraSettingsTab {
  id: string;
  label: string;
  panel: ReactNode;
}

const NO_EXTRA_TABS: ExtraSettingsTab[] = [];

const VALID_TABS: SettingsTab[] = [
  "profile",
  "preferences",
  "exam",
  "payments",
  "referrals",
  "memory",
];

/**
 * The retiring client's tabs, in its order, plus the tutor's memory.
 *
 * Referrals is admin-only, as it was there: the old `SettingsCore` pushed the
 * tab for `role === "admin"` and bounced `?tab=referrals` to Profile for
 * everybody else.
 */
const TABS: { id: SettingsTab; label: string; adminOnly?: boolean }[] = [
  { id: "profile", label: "Profile" },
  { id: "preferences", label: "Preferences" },
  { id: "exam", label: "Exam" },
  { id: "payments", label: "Payments" },
  { id: "referrals", label: "Referrals", adminOnly: true },
  { id: "memory", label: "Memory" },
];

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
  return (
    <Suspense fallback={<SettingsFrame tab="profile" onChange={() => {}} extraTabs={extraTabs} />}>
      <SettingsTabs extraTabs={extraTabs} />
    </Suspense>
  );
}

function SettingsTabs({ extraTabs }: { extraTabs: ExtraSettingsTab[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useSession();
  const isAdmin = isPlatformAdmin(session);
  const requested = searchParams.get("tab");
  const [fallback, setFallback] = useState<string>("profile");
  const known = isSettingsTab(requested)
    ? requested !== "referrals" || isAdmin
    : extraTabs.some((entry) => entry.id === requested);
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
  const { session } = useSession();
  const isAdmin = isPlatformAdmin(session);
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

  const items: B2CSegmentedTabItem<string>[] = [
    ...TABS.filter((entry) => !entry.adminOnly || isAdmin),
    ...extraTabs,
  ].map(({ id, label }) => ({ id, label }));

  const panels = (
    <>
      {tab === "profile" ? <ProfilePanel onDirtyChange={setDirty} /> : null}
      {tab === "preferences" ? <PreferencesPanel /> : null}
      {tab === "exam" ? <ExamPanel /> : null}
      {tab === "payments" ? <PaymentsPanel /> : null}
      {isAdmin && tab === "referrals" ? <ReferralsPanel /> : null}
      {tab === "memory" ? <TutorMemoryPanel /> : null}
      {extraTabs.map((entry) => (tab === entry.id ? <div key={entry.id}>{entry.panel}</div> : null))}
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
        description="Your own account: profile, sign-in and preferences."
        icon={HiOutlineCog6Tooth}
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
    <div>
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

function isSettingsTab(value: string | null): value is SettingsTab {
  return value !== null && (VALID_TABS as string[]).includes(value);
}
