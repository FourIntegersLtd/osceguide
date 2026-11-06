"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { useSession } from "@/foundation/session";
import { confirmPasswordReset, invitationOrganisation, login } from "@/foundation/platform-client";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { boardAlert } from "@/foundation/ui/boardKit";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthButton from "@/capabilities/account/AuthButton";
import AuthFormField from "@/capabilities/account/AuthFormField";
import AuthQuotePanel from "@/capabilities/account/AuthQuotePanel";
import { mapResetPasswordError } from "@/capabilities/account/support/mapAuthApiError";
import { invitationSubtitle } from "@/capabilities/account/support/invitationCopy";
import { afterPasswordReset } from "@/capabilities/account/support/afterPasswordReset";
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
  const { refresh, status, signOut } = useSession();
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
  const [organisationName, setOrganisationName] = useState<string | null>(null);
  const [after, setAfter] = useState<"sign_in_next" | "second_step" | "sign_in_failed">("sign_in_next");

  useEffect(() => {
    if (!invitation || !token) return;
    let current = true;
    void invitationOrganisation(token).then((name) => {
      if (current) setOrganisationName(name);
    });
    return () => {
      current = false;
    };
  }, [invitation, token]);

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
      // If the account needs a second step, or sign-in fails, the "Sign in" button is the way on.
      const next = await afterPasswordReset({
        invitation,
        endLocalSession: async () => {
          if (status !== "anonymous") await signOut();
        },
        signIn: async () => {
          // eslint-disable-next-line no-restricted-syntax -- null is handled on the next line as the "failed" outcome, shown by the form
          const outcome = await login(email, result.data.password).catch(() => null);
          if (outcome === null) return "failed";
          if (outcome.status !== "signed_in") return "second_step";
          await refresh();
          return "signed_in";
        },
      });
      if (next === "signed_in") router.replace("/app");
      else {
        setAfter(next);
        setDone(true);
      }
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
        compact
        title="This link is incomplete"
        subtitle={
          invitation
            ? "Open the link from your email again, or ask your administrator to resend it."
            : "Use the most recent email, or ask for a new link."
        }
      >
        <p data-auth-extra className={authFooterLink}>
          <Link href={invitation ? "/login" : "/forgot-password"} className={authLink}>
            {invitation ? "Sign in" : "Send a new link"}
          </Link>
        </p>
      </AuthShell>
    );
  }

  if (done) {
    return (
      <AuthShell
        variant="card"
        title={
          after === "sign_in_failed" ? "Password saved" : invitation ? "Your account is ready" : "Password changed"
        }
        subtitle={
          after === "sign_in_failed"
            ? "We saved it but could not sign you in just now. Sign in with the password you just chose."
            : after === "second_step"
              ? "Your account asks for a second step, so sign in to finish with your authenticator."
              : invitation
                ? "Sign in with the password you just chose."
                : "You can sign in with it now."
        }
      >
        <AuthButton type="button" onClick={() => router.replace("/login")}>
          Sign in
        </AuthButton>
      </AuthShell>
    );
  }

  const passwordToggle = (
    <button
      type="button"
      onClick={() => setFormData((prev) => ({ ...prev, showPassword: !prev.showPassword }))}
      data-auth-extra
      className="absolute inset-y-0 right-0 flex items-center pr-3 text-ink-subtle hover:text-ink-muted"
      aria-label={formData.showPassword ? "Hide password" : "Show password"}
    >
      {formData.showPassword ? <IoIosEyeOff className="h-5 w-5" /> : <IoIosEye className="h-5 w-5" />}
    </button>
  );

  return (
    <AuthShell
      variant={invitation ? "card" : "split"}
      sidePanel={invitation ? undefined : <AuthQuotePanel />}
      lead={invitation}
      compact={!invitation}
      title={invitation ? (organisationName ? `Join ${organisationName}` : "Accept your invitation") : "Choose a new password"}
      subtitle={
        invitation ? invitationSubtitle(organisationName) : "Choose something you'll remember"
      }
    >
      <form className="flex flex-col gap-3.5" method="post" onSubmit={handleFormSubmission} noValidate>
        <AuthFormField
          label={invitation ? "Password" : "New password"}
          hideLabel={!invitation}
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
          label={invitation ? "Confirm password" : "Confirm it"}
          hideLabel={!invitation}
          name="confirmPassword"
          type={formData.showPassword ? "text" : "password"}
          autoComplete="new-password"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
          error={fieldErrors.confirmPassword}
        />
        {formError ? (
          <div role="alert" className={boardAlert("bad")}>
            {formError}
          </div>
        ) : null}
        {linkSpent ? (
          <p className={authFooterLink}>
            <Link href={invitation ? "/login" : "/forgot-password"} className={authLink}>
              {invitation ? "Sign in" : "Send a new link"}
            </Link>
          </p>
        ) : null}
        <AuthButton isLoading={isSubmitting}>
          {isSubmitting ? "Saving…" : invitation ? "Accept invitation" : "Reset password"}
        </AuthButton>
      </form>
    </AuthShell>
  );
}
