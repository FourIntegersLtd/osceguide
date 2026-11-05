import type { SsoSignIn } from "@/capabilities/account/api";

/** What the sign-in page shows once the backend has said this account signs in
 *  through its organisation: the organisation's button, or why there is none. */
export interface SsoForRefusedPassword {
  sso: SsoSignIn | null;
  notice: string;
}

export const ORG_SIGN_IN_NOTICE = "This organisation signs in with its own sign-in. Use the button above.";
export const NO_ORG_DOOR_NOTICE =
  "This account signs in through your organisation, not with a password. Use the sign-in link your organisation gave you, or contact support.";
export const ORG_DOOR_UNREACHABLE_NOTICE =
  "This account signs in through your organisation, but we couldn't reach its sign-in just now. Try again in a moment.";

/**
 * A password refused with `password_login_disabled` means the arrival
 * discovery missed this person's organisation (another host, or it failed).
 * Ask again by their email address, so the page can offer the right door
 * instead of the same password form the backend will keep refusing.
 * The answer is forced to `sso_only`, because for this account it is.
 */
export async function ssoForRefusedPassword(
  email: string,
  lookup: (query: { email: string }) => Promise<SsoSignIn | null>,
): Promise<SsoForRefusedPassword> {
  try {
    const sso = await lookup({ email });
    if (!sso) return { sso: null, notice: NO_ORG_DOOR_NOTICE };
    return { sso: { ...sso, sso_only: true }, notice: ORG_SIGN_IN_NOTICE };
  } catch {
    return { sso: null, notice: ORG_DOOR_UNREACHABLE_NOTICE };
  }
}
