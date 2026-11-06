"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { AccountCreatedNotSignedIn, register } from "@/foundation/platform-client";
import { examAuthHref, normalizeExamCode } from "@/foundation/session/examCode";
import { PERSONAL_SLUG } from "@/foundation/routing/workspace";
import { useSession } from "@/foundation/session";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { boardAlert } from "@/foundation/ui/boardKit";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthButton from "@/capabilities/account/AuthButton";
import AuthFormField from "@/capabilities/account/AuthFormField";
import AuthQuotePanel from "@/capabilities/account/AuthQuotePanel";
import {
  PASSWORD_HINT,
  registerSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";
import { mapAuthApiError } from "@/capabilities/account/support/mapAuthApiError";
import { creditThisSignup } from "@/foundation/attribution/acquisition";

type RegisterField = "username" | "email" | "password" | "confirmPassword";

/**
 * Create an account.
 *
 * Consumers only. An institution provisions its people, and a trainee's first
 * sight of the product is an invitation rather than this form — which is why
 * there is no organisation field here and no way to ask for one.
 */
export default function Register() {
  const router = useRouter();
  const { refresh } = useSession();
  /*
   * Which exam they came to sit, from the per-exam landing pages' own links.
   *
   * This replaces the retiring client's subdomains: `sca.osceguide.com` set an
   * `appType` that every request carried, and the whole app was that one exam.
   * There is no picker here because the exam catalogue needs a token to read
   * and this form is the last screen before there is one — somebody who
   * arrives at the site root signs up without an exam, and the first screen
   * after this one asks for it (`ChooseExam`).
   */
  const examCode = normalizeExamCode(useSearchParams().get("appType"));

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    showPassword: false,
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<RegisterField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // The account exists but this browser is not signed in to it. The form
  // is spent (another submit would answer `email_taken`); signing in is next.
  const [accountCreated, setAccountCreated] = useState(false);

  const handleFormSubmission = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const result = validateWith<
      { username: string; email: string; password: string; confirmPassword: string },
      RegisterField
    >(registerSchema, {
      username: formData.username,
      email: formData.email,
      password: formData.password,
      confirmPassword: formData.confirmPassword,
    });
    if (!result.success) {
      setFieldErrors(result.fieldErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      const authenticated = await register({
        email: result.data.email,
        password: result.data.password,
        name: result.data.username,
        examCode,
      });
      await refresh();
      /*
       * Credit the partner who sent them, if anybody did. This is the spend for
       * the visitor key the edge minted on arrival, and it has to happen after
       * `refresh()` — the endpoint is authenticated, so it needs the token the
       * session has now adopted. Awaiting it rather than firing it loose so the
       * request survives the navigation that follows.
       */
      await creditThisSignup();
      // The backend's answer, not the link's: an exam it does not know is dropped there, and the
      // person then picks one on `/app`.
      const chosenExam = authenticated.user.exam_code ?? null;
      router.replace(chosenExam ? `/app/${PERSONAL_SLUG}` : "/app");
    } catch (error) {
      if (error instanceof AccountCreatedNotSignedIn) {
        setAccountCreated(true);
        setFormError(error.message);
        setIsSubmitting(false);
        return;
      }
      const mapped = mapAuthApiError<RegisterField>(
        error,
        "We couldn't create your account. Please try again.",
      );
      setFormError(mapped.formError);
      setFieldErrors(mapped.fieldErrors);
      setIsSubmitting(false);
    }
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>): void => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  };

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
      variant="split"
      title="Create your account"
      subtitle={
        examCode
          ? `Start practising for the ${examCode.toUpperCase()} in a few minutes`
          : "Start practising in a few minutes"
      }
      sidePanel={<AuthQuotePanel />}
    >
      <form className="flex flex-col gap-3.5" method="post" onSubmit={handleFormSubmission} noValidate>
        <AuthFormField
          label="Name"
          name="username"
          autoComplete="name"
          value={formData.username}
          onChange={handleChange}
          required
          error={fieldErrors.username}
        />
        <AuthFormField
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          value={formData.email}
          onChange={handleChange}
          required
          error={fieldErrors.email}
        />
        <AuthFormField
          label="Password"
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
          <div role="alert" className={boardAlert("bad")}>
            {formError}
            {accountCreated ? (
              <>
                {" "}
                <Link href={examAuthHref("/login", examCode)} className={authLink}>
                  Sign in
                </Link>
              </>
            ) : null}
          </div>
        ) : null}
        <AuthButton isLoading={isSubmitting} disabled={accountCreated}>
          {isSubmitting ? "Creating your account…" : "Create account"}
        </AuthButton>
      </form>

      <p className={authFooterLink}>
        Already have an account?{" "}
        <Link href={examAuthHref("/login", examCode)} className={authLink}>
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
