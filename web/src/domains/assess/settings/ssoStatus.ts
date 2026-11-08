import type { SsoStatus } from "@/domains/assess/api";

/** What the Settings tab says about the organisation's single sign-on, from the status alone. */
export function describeSsoStatus(status: SsoStatus): {
  badge: string;
  tone: "success" | "neutral" | "warning";
  detail: string;
} {
  if (!status.configured) {
    return { badge: "Not connected", tone: "neutral", detail: "People sign in with an email and password." };
  }
  if (!status.enabled) {
    return { badge: "Switched off", tone: "warning", detail: "Single sign-on is set up but switched off, so everyone signs in with a password." };
  }
  const label = status.sign_in_label ?? "single sign-on";
  return {
    badge: "Connected",
    tone: "success",
    detail: status.sso_only
      ? `Everyone signs in with “${label}”. Passwords are not accepted.`
      : `People can sign in with “${label}” or with a password.`,
  };
}
