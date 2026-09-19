"use client";

import { useState } from "react";
import { HiOutlineArrowPath, HiOutlineLockClosed } from "react-icons/hi2";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { z } from "zod";
import { changePassword, hasCode } from "@/foundation/platform-client";
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
  "w-full rounded-xl border border-osce-border bg-white px-3 py-2.5 text-osce-body text-osce-ink-900 outline-none transition focus:border-osce-accent-subtle focus:ring-2 focus:ring-osce-accent-muted";

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
 */
export default function ChangePassword() {
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
      setSuccessMessage("Password updated. Use it next time you sign in.");
      setValues({ currentPassword: "", newPassword: "", confirmPassword: "" });
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
                      <IoIosEyeOff className="h-4 w-4 text-osce-ink-400" />
                    ) : (
                      <IoIosEye className="h-4 w-4 text-osce-ink-400" />
                    )}
                  </button>
                </div>
                <B2CInlineError message={fieldErrors[name]} className="mt-1" />
                {hint && !fieldErrors[name] ? (
                  <p className="mt-1 text-osce-meta text-b2c-text-muted">{hint}</p>
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
