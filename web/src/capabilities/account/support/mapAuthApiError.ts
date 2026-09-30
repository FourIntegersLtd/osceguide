import { isPlatformError } from "@/foundation/platform-client";
import type { FieldErrors } from "@/capabilities/account/support/validateAuthForm";

export interface AuthApiErrorResult<TField extends string> {
  formError: string | null;
  fieldErrors: FieldErrors<TField>;
}

/**
 * Which field a validation failure is about, from the response body.
 *
 * FastAPI reports this as `details.errors[].loc`, e.g. `["body", "email"]`.
 * The retiring client had none of that — it matched the English message
 * against `/email/i` to guess — so rewording "Email already registered" moved
 * the error from under the email box to the top of the form. The structure was
 * always there; nothing read it.
 */
function fieldFromDetails(details: Record<string, unknown> | null): string | null {
  const errors = details?.errors;
  if (!Array.isArray(errors)) return null;
  for (const entry of errors) {
    const loc = (entry as { loc?: unknown })?.loc;
    if (!Array.isArray(loc)) continue;
    // `loc` is ["body", "<field>"]; the last segment is the field itself.
    const field = loc[loc.length - 1];
    if (typeof field === "string" && field !== "body") return field;
  }
  return null;
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

  const field = CODE_FIELDS[error.code] ?? fieldFromDetails(error.details);
  if (field) {
    return {
      formError: null,
      fieldErrors: { [field]: error.message } as FieldErrors<TField>,
    };
  }
  return { formError: error.message || fallback, fieldErrors: {} as FieldErrors<TField> };
}
