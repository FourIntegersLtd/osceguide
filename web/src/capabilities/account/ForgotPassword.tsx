"use client";

import Link from "next/link";
import { useEffect, useState, type ChangeEvent } from "react";
import { requestPasswordReset } from "@/foundation/platform-client";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { boardAlert } from "@/foundation/ui/boardKit";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthButton from "@/capabilities/account/AuthButton";
import AuthFormField from "@/capabilities/account/AuthFormField";
import AuthQuotePanel from "@/capabilities/account/AuthQuotePanel";
import { mapAuthApiError } from "@/capabilities/account/support/mapAuthApiError";
import {
  emailSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";
import { z } from "zod";

const schema = z.object({ email: emailSchema });

/** Seconds before the same address may be sent another link. */
const RESEND_AFTER_SECONDS = 30;

/**
 * Ask for a reset link.
 *
 * The confirmation says the same thing whether or not the address has an
 * account. Telling somebody "no account with that email" hands anybody who
 * asks a way to test which of a list of addresses is registered here, and a
 * medical exam platform's user list is not a neutral fact about a person.
 */
export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<"email">>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [wait, setWait] = useState(0);

  useEffect(() => {
    if (wait <= 0) return;
    const timer = setTimeout(() => setWait((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [wait]);

  const handleFormSubmission = async (event: React.FormEvent) => {
    event.preventDefault();
    if (wait > 0) return;
    setFormError(null);
    const result = validateWith<{ email: string }, "email">(schema, { email });
    if (!result.success) {
      setFieldErrors(result.fieldErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      await requestPasswordReset(result.data.email);
      setSent(true);
      setWait(RESEND_AFTER_SECONDS);
    } catch (cause) {
      // A rate limit says to wait rather than to try again at once.
      const refused = mapAuthApiError<"email">(cause, "We couldn't send the email. Please try again.");
      setFormError(refused.formError);
      setFieldErrors(refused.fieldErrors);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (sent) {
    return (
      <AuthShell
        variant="card"
        title="Check your email"
        subtitle={`If ${email} has a password account, a reset link is on its way.`}
      >
        <p className={authFooterLink}>
          The link works for one hour. If your organisation signs you in with its own account, no
          email is sent: use &ldquo;Sign in with&rdquo; on the sign-in page instead.
        </p>
        <p className={authFooterLink}>
          Nothing arrived?{" "}
          <button
            type="button"
            disabled={wait > 0 || isSubmitting}
            onClick={(event) => void handleFormSubmission(event)}
            className={authLink}
          >
            {wait > 0 ? `Send again in ${wait}s` : "Send again"}
          </button>
          {" · "}
          <button type="button" onClick={() => setSent(false)} className={authLink}>
            Try another address
          </button>
        </p>
        <p className={authFooterLink}>
          <Link href="/login" className={authLink}>
            Back to sign in
          </Link>
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      variant="split"
      title="Reset your password"
      subtitle="We email you a link if an account uses this address."
      sidePanel={<AuthQuotePanel />}
    >
      <form className="flex flex-col gap-3.5" method="post" onSubmit={handleFormSubmission} noValidate>
        <AuthFormField
          label="Email"
          hideLabel
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
            setEmail(event.target.value);
            setFieldErrors({});
          }}
          required
          error={fieldErrors.email}
        />
        {formError ? (
          <div role="alert" className={boardAlert("bad")}>
            {formError}
          </div>
        ) : null}
        <AuthButton isLoading={isSubmitting}>
          {isSubmitting ? "Sending…" : "Send the link"}
        </AuthButton>
      </form>

      <p data-auth-extra className={authFooterLink}>
        Remembered it?{" "}
        <Link href="/login" className={authLink}>
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
