"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { Button } from "@/foundation/ui";
import { confirmPasswordReset } from "@/foundation/platform-client";
import { authButtonPrimary, authFooterLink, authLink } from "@/foundation/ui/authTheme";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthFormField from "@/capabilities/account/AuthFormField";
import {
  PASSWORD_HINT,
  resetPasswordSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";

type ResetField = "password" | "confirmPassword";

/**
 * Set a new password from an emailed link.
 *
 * A missing or refused token is the same screen either way: expired, already
 * used, or never valid are indistinguishable to the person holding it, and
 * distinguishing them out loud would tell somebody testing tokens which of
 * their guesses were real.
 */
export default function ResetPassword() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
    showPassword: false,
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<ResetField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleFormSubmission = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const result = validateWith<{ password: string; confirmPassword: string }, ResetField>(
      resetPasswordSchema,
      { password: formData.password, confirmPassword: formData.confirmPassword },
    );
    if (!result.success) {
      setFieldErrors(result.fieldErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      await confirmPasswordReset(token, result.data.password);
      setDone(true);
    } catch {
      setFormError(
        "That link is no longer valid. Ask for a new one and use the most recent email.",
      );
      setIsSubmitting(false);
    }
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  };

  if (!token) {
    return (
      <AuthShell
        variant="card"
        title="That link is incomplete"
        subtitle="Use the most recent email, or ask for a new link."
      >
        <p className={authFooterLink}>
          <Link href="/forgot-password" className={authLink}>
            Send a new link
          </Link>
        </p>
      </AuthShell>
    );
  }

  if (done) {
    return (
      <AuthShell variant="card" title="Password changed" subtitle="You can sign in with it now.">
        <Button
          type="button"
          variant="commit"
          themeType="b2c"
          fullWidth
          size="lg"
          className={authButtonPrimary}
          onClick={() => router.replace("/login")}
        >
          Sign in
        </Button>
      </AuthShell>
    );
  }

  const passwordToggle = (
    <button
      type="button"
      onClick={() => setFormData((prev) => ({ ...prev, showPassword: !prev.showPassword }))}
      className="absolute inset-y-0 right-0 flex items-center pr-3 text-ink-subtle hover:text-ink-muted"
      aria-label={formData.showPassword ? "Hide password" : "Show password"}
    >
      {formData.showPassword ? <IoIosEyeOff className="h-5 w-5" /> : <IoIosEye className="h-5 w-5" />}
    </button>
  );

  return (
    <AuthShell variant="card" title="Set a new password" subtitle="Choose something you'll remember">
      <form className="space-y-5" onSubmit={handleFormSubmission} noValidate>
        <AuthFormField
          label="New password"
          name="password"
          type={formData.showPassword ? "text" : "password"}
          autoComplete="new-password"
          value={formData.password}
          onChange={handleChange}
          required
          hint={PASSWORD_HINT}
          suffix={passwordToggle}
          error={fieldErrors.password}
        />
        <AuthFormField
          label="Confirm password"
          name="confirmPassword"
          type={formData.showPassword ? "text" : "password"}
          autoComplete="new-password"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
          error={fieldErrors.confirmPassword}
        />
        {formError ? (
          <p role="alert" className="text-center text-osce-meta text-osce-danger">
            {formError}
          </p>
        ) : null}
        <Button
          type="submit"
          variant="commit"
          themeType="b2c"
          fullWidth
          size="lg"
          isLoading={isSubmitting}
          className={authButtonPrimary}
        >
          {isSubmitting ? "Saving…" : "Save new password"}
        </Button>
      </form>
    </AuthShell>
  );
}
