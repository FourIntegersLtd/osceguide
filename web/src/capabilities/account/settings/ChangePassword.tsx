"use client";

import { useState } from "react";
import { HiOutlineArrowPath, HiOutlineLockClosed } from "react-icons/hi2";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { z } from "zod";
import { changePassword, hasCode, isPlatformError, requestPasswordReset } from "@/foundation/platform-client";
import { useSession } from "@/foundation/session";
import {
  B2CInlineError,
  ModalContent,
  ModalField,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSection,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { errorMessage } from "@/foundation/hooks";
import {
  PASSWORD_HINT,
  passwordSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";

const inputClassName =
  "w-full rounded-xl border border-osce-border bg-white px-3 py-2.5 text-osce-body text-ink outline-none transition focus:border-osce-accent-subtle focus:ring-2 focus:ring-osce-accent-muted";

const updatePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, "Enter your current password"),
    newPassword: passwordSchema,
    confirmPassword: z.string(),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

type PasswordField = "currentPassword" | "newPassword" | "confirmPassword";

/** An account with no password to prove (an invitation finished through
 *  SSO). Not in the generated codes until `openapi.json` is regenerated. */
const PASSWORD_NOT_SET = "password_not_set";

const FIELDS: { name: PasswordField; label: string; hint?: string }[] = [
  { name: "currentPassword", label: "Current Password" },
  { name: "newPassword", label: "New Password", hint: PASSWORD_HINT },
  { name: "confirmPassword", label: "Confirm New Password" },
];

/**
 * Change your own password, on whichever arm you are standing in.
 *
 * The retiring client had this under the consumer settings only, so an
 * institution's supervisor — who signs off results — had no way to rotate
 * their own password without an administrator. It is the same endpoint for
 * everybody, so it is the same screen for everybody.
 *
 * `onChanged` is what tells the two callers apart. Left out, the card stays
 * put and simply says it worked — which is right inside Settings. Supplied by
 * the forced screen, it runs after the success message lands, so the session
 * can be re-read and the person sent on.
 */
export default function ChangePassword({ onChanged }: { onChanged?: () => Promise<void> }) {
  const [values, setValues] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [shown, setShown] = useState<Record<PasswordField, boolean>>({
    currentPassword: false,
    newPassword: false,
    confirmPassword: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<PasswordField>>({});
  const [noPassword, setNoPassword] = useState(false);
  const email = useSession().session?.user.email ?? null;

  const sendSetPasswordLink = async () => {
    if (!email) return;
    setFormError(null);
    try {
      await requestPasswordReset(email);
      setNoPassword(false);
      setSuccessMessage(`We've emailed ${email} a link to set a password.`);
    } catch (error) {
      setFormError(errorMessage(error));
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);
    const validation = validateWith<typeof values, PasswordField>(
      updatePasswordSchema,
      values,
    );
    if (!validation.success) {
      setFieldErrors(validation.fieldErrors);
      return;
    }
    setFieldErrors({});
    setIsSubmitting(true);
    try {
      await changePassword(values.currentPassword, values.newPassword);
      setSuccessMessage("Password updated. Your other devices have been signed out; this one stays signed in.");
      setValues({ currentPassword: "", newPassword: "", confirmPassword: "" });
      if (onChanged) await onChanged();
    } catch (error) {
      /*
       * The code, never the wording. The retiring screen branched on HTTP 401
       * or 403, which is also what an expired session answers — so a person
       * whose token had lapsed was told their current password was wrong.
       */
      if (hasCode(error, "invalid_credentials")) {
        setFieldErrors({ currentPassword: "That's not your current password." });
      } else if (hasCode(error, "weak_password")) {
        setFieldErrors({ newPassword: errorMessage(error) });
      } else if (isPlatformError(error) && (error.code as string) === PASSWORD_NOT_SET) {
        setNoPassword(true);
        setFormError("This account has no password yet, so there is none to change. We can email you a link to set one.");
      } else {
        setFormError(errorMessage(error));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ModalContent>
      <ModalLead
        title="Update password"
        description="Choose a new password for your account."
        icon={<HiOutlineLockClosed className="h-5 w-5" />}
      />
      {successMessage ? <Alert message={successMessage} type="success" /> : null}
      {formError ? <Alert message={formError} type="error" /> : null}
      {noPassword && email ? (
        <ModalPrimaryButton type="button" onClick={() => void sendSetPasswordLink()}>
          Email me a link
        </ModalPrimaryButton>
      ) : null}

      <form onSubmit={handleSubmit} noValidate className="space-y-7">
        <ModalSection title="Password details">
          <div className="space-y-4">
            {FIELDS.map(({ name, label, hint }) => (
              <ModalField key={name} label={label} htmlFor={name}>
                <div className="relative">
                  <input
                    type={shown[name] ? "text" : "password"}
                    id={name}
                    value={values[name]}
                    onChange={(event) =>
                      setValues({ ...values, [name]: event.target.value })
                    }
                    className={`${inputClassName} pr-10`}
                    required
                    aria-invalid={fieldErrors[name] ? true : undefined}
                  />
                  <button
                    type="button"
                    aria-label={shown[name] ? "Hide password" : "Show password"}
                    onClick={() => setShown({ ...shown, [name]: !shown[name] })}
                    className="absolute inset-y-0 right-0 flex items-center pr-3"
                  >
                    {shown[name] ? (
                      <IoIosEyeOff className="h-4 w-4 text-ink-subtle" />
                    ) : (
                      <IoIosEye className="h-4 w-4 text-ink-subtle" />
                    )}
                  </button>
                </div>
                <B2CInlineError message={fieldErrors[name]} className="mt-1" />
                {hint && !fieldErrors[name] ? (
                  <p className="mt-1 text-osce-meta text-ink-subtle">{hint}</p>
                ) : null}
              </ModalField>
            ))}
          </div>
        </ModalSection>
        <ModalFooterActions>
          <ModalPrimaryButton type="submit" disabled={isSubmitting} className="gap-2">
            {isSubmitting ? (
              <>
                <HiOutlineArrowPath className="h-3.5 w-3.5 animate-spin" /> Updating...
              </>
            ) : (
              "Update password"
            )}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </form>
    </ModalContent>
  );
}
