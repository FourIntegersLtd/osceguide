import { isOrgSurface } from "@/capabilities/surface";

/** Staff settings split the Profile tab in three; `ProfilePanel` renders one part. */
export type ProfilePart = "account" | "security" | "data";

export type SettingsTab =
  | "profile"
  | "preferences"
  | "payments"
  | "referrals"
  | ProfilePart;

/**
 * Referrals and Payments are for consumers: checkout accepts a code from any
 * buyer and `POST /me/referral-code` issues one to any signed-in account. An
 * institution's or employer's access is arranged offline, so those arms get
 * Profile and Preferences only.
 */
const TABS: { id: SettingsTab; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "preferences", label: "Preferences" },
  { id: "payments", label: "Payments" },
  { id: "referrals", label: "Referrals" },
];

/**
 * Staff settings: staff have no exam, plan, referrals or tutor, so they get
 * the Profile tab's three parts and nothing that would only say "upgrade".
 */
const PLATFORM_TABS: { id: SettingsTab; label: string }[] = [
  { id: "account", label: "Account" },
  { id: "security", label: "Security" },
  { id: "data", label: "Data" },
];

/** The person's own two tabs on an organisation's arm: the Settings board calls the first "Your account". */
const ORG_TABS = TABS.filter((tab) => tab.id === "profile" || tab.id === "preferences").map((tab) =>
  tab.id === "profile" ? { ...tab, label: "Your account" } : tab,
);

export const tabsFor = (surface: string) =>
  surface === "platform" ? PLATFORM_TABS : isOrgSurface(surface) ? ORG_TABS : TABS;

/**
 * The strip an arm's extra tabs make with the person's own: extras first (an organisation's
 * own settings open the strip), then the person's, then any extra marked `after`.
 */
export function arrangeTabs<E extends { id: string; label: string; after?: boolean }>(
  own: readonly { id: string; label: string }[],
  extras: readonly E[],
): { id: string; label: string }[] {
  return [
    ...extras.filter((entry) => !entry.after),
    ...own,
    ...extras.filter((entry) => entry.after),
  ].map(({ id, label }) => ({ id, label }));
}
