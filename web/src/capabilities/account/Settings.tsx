"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { IconType } from "react-icons";
import {
  HiOutlineAcademicCap,
  HiOutlineAdjustmentsHorizontal,
  HiOutlineCog6Tooth,
  HiOutlineCreditCard,
  HiOutlineGift,
  HiOutlineSparkles,
  HiOutlineUser,
} from "react-icons/hi2";
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
const TABS: { id: SettingsTab; label: string; icon: IconType; adminOnly?: boolean }[] = [
  { id: "profile", label: "Profile", icon: HiOutlineUser },
  { id: "preferences", label: "Preferences", icon: HiOutlineAdjustmentsHorizontal },
  { id: "exam", label: "Exam", icon: HiOutlineAcademicCap },
  { id: "payments", label: "Payments", icon: HiOutlineCreditCard },
  { id: "referrals", label: "Referrals", icon: HiOutlineGift, adminOnly: true },
  { id: "memory", label: "Memory", icon: HiOutlineSparkles },
];

/**
 * The person, on whichever arm they are standing.
 *
 * Mounted on all five surfaces deliberately. The retiring client had settings
 * under the consumer arm only, which meant an institution's supervisor — the
 * person who signs off results — could not change their own password. Nothing
 * on this screen is consumer-specific: everybody has a name, a password, the
 * access they were granted or bought, and a tutor keeping notes on them.
 */
export function Settings() {
  return (
    <Suspense fallback={<SettingsFrame tab="profile" onChange={() => {}} />}>
      <SettingsTabs />
    </Suspense>
  );
}

function SettingsTabs() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { session } = useSession();
  const isAdmin = isPlatformAdmin(session);
  const requested = searchParams.get("tab");
  const [fallback, setFallback] = useState<SettingsTab>("profile");
  const tab = isSettingsTab(requested) && (requested !== "referrals" || isAdmin) ? requested : fallback;

  /*
   * The query string is the source of truth when it names a tab, so a link to
   * "?tab=payments" — the one the cancelled-checkout page sends people back
   * to — opens on the right panel. State only fills in before anybody has
   * chosen, which keeps the two from disagreeing on a back navigation.
   */
  const handleChange = (next: SettingsTab) => {
    setFallback(next);
    router.push(`?tab=${next}`, { scroll: false });
  };

  return <SettingsFrame tab={tab} onChange={handleChange} />;
}

function SettingsFrame({
  tab,
  onChange,
}: {
  tab: SettingsTab;
  onChange: (tab: SettingsTab) => void;
}) {
  const { surface } = useSurface();
  const { session } = useSession();
  const isAdmin = isPlatformAdmin(session);
  // The old screen's unsaved-changes guard: an edited, unsaved username stops
  // a tab switch (and a page unload) until the person says so.
  const [isDirty, setDirty] = useState(false);
  const [pendingTab, setPendingTab] = useState<SettingsTab | null>(null);

  useEffect(() => {
    if (!isDirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const handleTabChange = (next: SettingsTab) => {
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

  const items: B2CSegmentedTabItem<SettingsTab>[] = TABS.filter(
    (entry) => !entry.adminOnly || isAdmin,
  ).map(({ id, label, icon: Icon }) => ({
    id,
    label: (
      <span className="inline-flex items-center gap-1.5">
        <Icon className="h-4 w-4" aria-hidden />
        {label}
      </span>
    ),
  }));

  const panels = (
    <>
      {tab === "profile" ? <ProfilePanel onDirtyChange={setDirty} /> : null}
      {tab === "preferences" ? <PreferencesPanel /> : null}
      {tab === "exam" ? <ExamPanel /> : null}
      {tab === "payments" ? <PaymentsPanel /> : null}
      {isAdmin && tab === "referrals" ? <ReferralsPanel /> : null}
      {tab === "memory" ? <TutorMemoryPanel /> : null}
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
      <B2CPageHeader title="Settings" icon={HiOutlineCog6Tooth} />
      <B2CSegmentedTabs
        className="mb-8"
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
