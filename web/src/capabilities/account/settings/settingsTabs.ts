/** Staff settings split the Profile tab in three; `ProfilePanel` renders one part. */
export type ProfilePart = "account" | "security" | "data";

export type SettingsTab =
  | "profile"
  | "preferences"
  | "payments"
  | "referrals"
  | ProfilePart;

/**
 * Referrals is for everyone: checkout accepts a code from any buyer and
 * `POST /me/referral-code` issues one to any signed-in account. (The old
 * screen hid it from non-admins, which left a referee with no way to find
 * their own code.)
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

export const tabsFor = (surface: string) => (surface === "platform" ? PLATFORM_TABS : TABS);
