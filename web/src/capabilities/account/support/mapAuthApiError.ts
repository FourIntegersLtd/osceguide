import { isPlatformError, validationFields } from "@/foundation/platform-client";
import type { FieldErrors } from "@/capabilities/account/support/validateAuthForm";

export interface AuthApiErrorResult<TField extends string> {
  formError: string | null;
  fieldErrors: FieldErrors<TField>;
}

/** Codes that are unambiguously about one field, whatever the wording. */
const CODE_FIELDS: Record<string, string> = {
  email_taken: "email",
  invalid_credentials: "password",
  weak_password: "password",
};

/**
 * Turn a backend auth failure into an inline field error where the backend
 * says which field it is, and a form-level error otherwise.
 */
export function mapAuthApiError<TField extends string>(
  error: unknown,
  fallback: string,
): AuthApiErrorResult<TField> {
  if (!isPlatformError(error)) {
    return { formError: fallback, fieldErrors: {} as FieldErrors<TField> };
  }

  // Which field the backend says it is about (`details.errors[].loc`), rather than
  // guessing from the English message, which moved the error whenever it was reworded.
  const field = CODE_FIELDS[error.code] ?? Object.keys(validationFields(error))[0] ?? null;
  if (field) {
    return {
      formError: null,
      fieldErrors: { [field]: error.message } as FieldErrors<TField>,
    };
  }
  return { formError: error.message || fallback, fieldErrors: {} as FieldErrors<TField> };
}

export interface ResetPasswordErrorResult extends AuthApiErrorResult<"password" | "confirmPassword"> {
  /** The link itself is spent or expired: offer the way on, not another try. */
  linkSpent: boolean;
}

/**
 * Why `password-reset/confirm` refused. Only `invalid_reset_token` is about the link;
 * a weak password or a rate limit leaves it good, and saying "no longer valid" then
 * sent people to ask for a new link that would fail the same way.
 *
 * Spent, expired and never-valid stay one sentence (telling them apart would tell
 * somebody guessing tokens which guesses were real). An invited person who clicks the
 * email again after choosing a password is the common case, so that sentence says to
 * sign in: re-sending is refused for an account that already has a password.
 */
export function mapResetPasswordError(error: unknown, invitation: boolean): ResetPasswordErrorResult {
  if (isPlatformError(error) && error.code === "invalid_reset_token") {
    return {
      formError: invitation
        ? "That invitation has already been used or has expired. If you already chose a password, sign in. Otherwise ask the person who invited you to send it again."
        : "That link is no longer valid. Ask for a new one and use the most recent email.",
      fieldErrors: {},
      linkSpent: true,
    };
  }
  return {
    ...mapAuthApiError<"password" | "confirmPassword">(error, "We couldn't save your password. Please try again."),
    linkSpent: false,
  };
}
