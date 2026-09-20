"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { B2CSegmentedTabs, type B2CSegmentedTabItem } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { PlatformTabbedScreen } from "@/domains/platform/PlatformTabbedScreen";
import ProfilePanel from "@/capabilities/account/settings/ProfilePanel";
import PreferencesPanel from "@/capabilities/account/settings/PreferencesPanel";
import ExamPanel from "@/capabilities/account/settings/ExamPanel";
import AccessPanel from "@/capabilities/account/settings/AccessPanel";
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
 * "Access" was this tab's label for a while and is "Payments" again: the old
 * one said Payments, and it is where somebody looks for a receipt. It was also
 * a nav item of its own for a while, rendering the same panel — one screen in
 * two places, neither of them canonical.
 */
const TABS: { id: SettingsTab; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "preferences", label: "Preferences" },
  { id: "exam", label: "Exam" },
  { id: "payments", label: "Payments" },
  { id: "referrals", label: "Referrals" },
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
 * Referrals is shown to everybody rather than to admins, as the old one did.
 * The backend issues a code per person and counts redemptions per person;
 * hiding the screen from most of them hid the feature, not a permission.
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
  const requested = searchParams.get("tab");
  const [fallback, setFallback] = useState<SettingsTab>("profile");
  const tab = isSettingsTab(requested) ? requested : fallback;

  /*
   * The query string is the source of truth when it names a tab, so a link to
   * "?tab=payments" — the one the cancelled-checkout page sends people back
   * to — opens on the right panel. State only fills in before anybody has
   * chosen, which keeps the two from disagreeing on a back navigation.
   */
  const handleChange = (next: SettingsTab) => {
    setFallback(next);
    router.replace(`?tab=${next}`, { scroll: false });
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
  const items: B2CSegmentedTabItem<SettingsTab>[] = TABS.map(({ id, label }) => ({
    id,
    label,
  }));

  const panels = (
    <>
      {tab === "profile" ? <ProfilePanel /> : null}
      {tab === "preferences" ? <PreferencesPanel /> : null}
      {tab === "exam" ? <ExamPanel /> : null}
      {tab === "payments" ? <AccessPanel /> : null}
      {tab === "referrals" ? <ReferralsPanel /> : null}
      {tab === "memory" ? <TutorMemoryPanel /> : null}
    </>
  );

  if (surface === "platform") {
    return (
      <PlatformTabbedScreen
        title="Settings"
        tabs={items}
        value={tab}
        onChange={onChange}
        ariaLabel="Settings"
      >
        {panels}
      </PlatformTabbedScreen>
    );
  }

  return (
    <div>
      <B2CSegmentedTabs
        items={items}
        value={tab}
        onChange={onChange}
        aria-label="Settings"
      />
      <div>{panels}</div>
    </div>
  );
}

function isSettingsTab(value: string | null): value is SettingsTab {
  return value !== null && (VALID_TABS as string[]).includes(value);
}
