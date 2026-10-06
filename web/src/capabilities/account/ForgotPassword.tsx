"use client";

import Link from "next/link";
import { useState, type ChangeEvent } from "react";
import { Button } from "@/foundation/ui";
import { requestPasswordReset } from "@/foundation/platform-client";
import { authButtonPrimary, authFooterLink, authLink } from "@/foundation/ui/authTheme";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthFormField from "@/capabilities/account/AuthFormField";
import { mapAuthApiError } from "@/capabilities/account/support/mapAuthApiError";
import {
  emailSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";
import { z } from "zod";

const schema = z.object({ email: emailSchema });

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

  const handleFormSubmission = async (event: React.FormEvent) => {
    event.preventDefault();
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
        subtitle={`If an account exists for ${email}, a reset link is on its way.`}
      >
        <p className={authFooterLink}>
          The link expires shortly. Nothing arrived?{" "}
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
      variant="card"
      title="Reset your password"
      subtitle="We'll email you a link to set a new one"
    >
      <form className="space-y-5" onSubmit={handleFormSubmission} noValidate>
        <AuthFormField
          label="Email"
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
          {isSubmitting ? "Sending…" : "Send reset link"}
        </Button>
      </form>

      <p className={authFooterLink}>
        Remembered it?{" "}
        <Link href="/login" className={authLink}>
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
