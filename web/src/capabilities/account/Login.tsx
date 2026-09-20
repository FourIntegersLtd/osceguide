"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { Button } from "@/foundation/ui";
import { login } from "@/foundation/platform-client";
import { examAuthHref, normalizeExamCode, rememberExamSelection } from "@/foundation/session/examSelection";
import { PERSONAL_SLUG } from "@/foundation/routing/workspace";
import { useSession } from "@/foundation/session";
import {
  authButtonPrimary,
  authFooterLink,
  authLink,
} from "@/foundation/ui/authTheme";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthFormField from "@/capabilities/account/AuthFormField";
import AuthQuotePanel from "@/capabilities/account/AuthQuotePanel";
import { sanitizeReturnTo } from "@/capabilities/account/support/sessionEvents";
import {
  loginSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";
import { mapAuthApiError } from "@/capabilities/account/support/mapAuthApiError";

type LoginField = "email" | "password";

/**
 * One sign-in, for every product.
 *
 * The retiring system had five login pages — consumer, institution, partner,
 * practice and the staff console — and which one you used decided which
 * workspace you landed in. Identity is one table and one token now, so the
 * landing is chosen afterwards from what the person belongs to. That is
 * `/app`'s job, and this screen simply gets them a session and sends them
 * there.
 *
 * Gone with the five pages: the exam picker (which exam you are practising for
 * is an entitlement, not something to choose at the door) and the SSO button
 * (`platform-api` has no tenant SSO yet — see `docs/port-gaps.md`).
 */
export default function Login() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const examCode = normalizeExamCode(searchParams.get("appType"));
  const { refresh } = useSession();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    showPassword: false,
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<LoginField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFormSubmission = async (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    const result = validateWith<{ email: string; password: string }, LoginField>(
      loginSchema,
      { email: formData.email, password: formData.password },
    );
    if (!result.success) {
      setFieldErrors(result.fieldErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      const authenticated = await login(result.data.email, result.data.password);
      rememberExamSelection(authenticated.user.id, examCode);
      await refresh();
      const returnTo = sanitizeReturnTo(searchParams.get("next") ?? searchParams.get("returnTo"));
      // Keep the button pending; the page is about to change. `/app` decides
      // which workspace, from where they were last.
      router.replace(returnTo ?? (examCode ? `/app/${PERSONAL_SLUG}` : "/app"));
    } catch (error) {
      const mapped = mapAuthApiError<LoginField>(
        error,
        "We couldn't sign you in. Check your details and try again.",
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

  const handleTogglePassword = () => {
    setFormData((prev) => ({ ...prev, showPassword: !prev.showPassword }));
  };

  const passwordToggle = (
    <button
      type="button"
      onClick={handleTogglePassword}
      className="absolute inset-y-0 right-0 flex items-center pr-3 text-b2c-text-muted hover:text-b2c-text-secondary"
      aria-label={formData.showPassword ? "Hide password" : "Show password"}
    >
      {formData.showPassword ? (
        <IoIosEyeOff className="h-5 w-5" />
      ) : (
        <IoIosEye className="h-5 w-5" />
      )}
    </button>
  );

  return (
    <AuthShell
      variant="split"
      title="Welcome back"
      subtitle="Sign in to your account"
      sidePanel={<AuthQuotePanel />}
    >
      <form className="space-y-5" onSubmit={handleFormSubmission} noValidate>
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
          autoComplete="current-password"
          value={formData.password}
          onChange={handleChange}
          required
          suffix={passwordToggle}
          error={fieldErrors.password}
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
          {isSubmitting ? "Signing you in…" : "Sign in"}
        </Button>
      </form>

      <div className="space-y-3">
        <p className={authFooterLink}>
          Forgot your password?{" "}
          <Link href="/forgot-password" className={authLink}>
            Reset password
          </Link>
        </p>
        <p className={authFooterLink}>
          Don&apos;t have an account?{" "}
          <Link href={examAuthHref("/register", examCode)} className={authLink}>
            Create account
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
