"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { Button } from "@/foundation/ui";
import { useHydrated } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { confirmPasswordReset, login } from "@/foundation/platform-client";
import { authButtonPrimary, authFooterLink, authLink } from "@/foundation/ui/authTheme";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthFormField from "@/capabilities/account/AuthFormField";
import { mapResetPasswordError } from "@/capabilities/account/support/mapAuthApiError";
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
 * their guesses were real. Any other refusal (a weak password, a rate limit)
 * is said as itself: the link is still good (`mapResetPasswordError`).
 *
 * `invitation` is the same act for somebody new: an invitation's token is a
 * reset token, so `/accept-invitation` is this screen with its own wording.
 */
export default function ResetPassword({ invitation = false }: { invitation?: boolean }) {
  const router = useRouter();
  const { refresh } = useSession();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: "",
    showPassword: false,
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<ResetField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [linkSpent, setLinkSpent] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  // Until hydrated the submit is inert: a native submit would put the password in the URL.
  const hydrated = useHydrated();

  const signInAfterInvitation = async (email: string, password: string) => {
    const outcome = await login(email, password).catch(() => null);
    if (outcome?.status !== "signed_in") return;
    await refresh();
    router.replace("/app");
  };

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
      const email = await confirmPasswordReset(token, result.data.password);
      setDone(true);
      // An invitation signs the new account in with the password just chosen. A plain reset
      // ends every session on purpose, so it goes back to the sign-in screen instead. If the
      // account needs a second step, or sign-in fails, the "Sign in" button is the way on.
      if (invitation) await signInAfterInvitation(email, result.data.password);
    } catch (cause) {
      const refused = mapResetPasswordError(cause, invitation);
      setFormError(refused.formError);
      setFieldErrors(refused.fieldErrors);
      setLinkSpent(refused.linkSpent);
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
      <AuthShell
        variant="card"
        title={invitation ? "Your account is ready" : "Password changed"}
        subtitle={invitation ? "Sign in with the password you just chose." : "You can sign in with it now."}
      >
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
    <AuthShell
      variant="card"
      eyebrow={invitation ? "Invitation" : undefined}
      title={invitation ? "Accept your invitation" : "Set a new password"}
      subtitle={
        invitation ? "Choose a password to finish setting up your account." : "Choose something you'll remember"
      }
    >
      <form className="space-y-5" method="post" onSubmit={handleFormSubmission} noValidate>
        <AuthFormField
          label={invitation ? "Password" : "New password"}
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
        {linkSpent ? (
          <p className={authFooterLink}>
            <Link href={invitation ? "/login" : "/forgot-password"} className={authLink}>
              {invitation ? "Sign in" : "Send a new link"}
            </Link>
          </p>
        ) : null}
        <Button
          type="submit"
          variant="commit"
          themeType="b2c"
          fullWidth
          size="lg"
          isLoading={isSubmitting}
          disabled={!hydrated}
          className={authButtonPrimary}
        >
          {isSubmitting ? "Saving…" : invitation ? "Accept invitation" : "Save new password"}
        </Button>
      </form>
    </AuthShell>
  );
}
