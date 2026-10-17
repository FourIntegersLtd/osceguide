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

const ORG_TABS = TABS.filter((tab) => tab.id === "profile" || tab.id === "preferences");

export const tabsFor = (surface: string) =>
  surface === "platform" ? PLATFORM_TABS : isOrgSurface(surface) ? ORG_TABS : TABS;
