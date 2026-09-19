/** Reads one-shot notices passed to the login page via query params (React-free). */

export type AuthNoticeTone = "success" | "error" | "info";

export interface AuthNotice {
  tone: AuthNoticeTone;
  message: string;
}

export const AUTH_NOTICE_PARAMS = ["reset", "reason", "sso_error", "registered", "deleted"] as const;

const SSO_ERROR_MESSAGES: Record<string, string> = {
  cancelled: "Sign-in was cancelled. You can try again whenever you're ready.",
  not_provisioned:
    "Your organisation account isn't set up on OSCE Guide yet. Contact your administrator or our support team.",
  invalid_tenant: "We couldn't match your organisation. Contact support and mention \"SSO sign-in\".",
};

const DEFAULT_SSO_ERROR =
  "We couldn't sign you in with your organisation account. Please try again. If this keeps happening, contact support and mention \"SSO sign-in\".";

export function readAuthNotice(params: URLSearchParams): AuthNotice | null {
  if (params.get("reset") === "success") {
    return { tone: "success", message: "Password updated. Sign in with your new password." };
  }
  if (params.get("deleted") === "1") {
    return { tone: "success", message: "Your account has been deleted. We're sorry to see you go." };
  }
  if (params.get("registered") === "1") {
    return { tone: "success", message: "Account created. Sign in to continue." };
  }
  if (params.get("reason") === "session_expired") {
    return {
      tone: "info",
      message: "Your session has expired. Please sign in again to continue.",
    };
  }
  const ssoError = params.get("sso_error");
  if (ssoError !== null) {
    return {
      tone: "error",
      message: SSO_ERROR_MESSAGES[ssoError.toLowerCase()] ?? DEFAULT_SSO_ERROR,
    };
  }
  return null;
}

/** Removes consumed notice params so a refresh doesn't repeat the message. */
export function stripAuthNoticeParams(params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params);
  AUTH_NOTICE_PARAMS.forEach((key) => next.delete(key));
  return next;
}
