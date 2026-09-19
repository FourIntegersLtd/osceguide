"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { Button } from "@/foundation/ui";
import { register } from "@/foundation/platform-client";
import { useSession } from "@/foundation/session";
import { authButtonPrimary, authFooterLink, authLink } from "@/foundation/ui/authTheme";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthFormField from "@/capabilities/account/AuthFormField";
import AuthQuotePanel from "@/capabilities/account/AuthQuotePanel";
import {
  PASSWORD_HINT,
  registerSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";
import { mapAuthApiError } from "@/capabilities/account/support/mapAuthApiError";

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
      await register({
        email: result.data.email,
        password: result.data.password,
        name: result.data.username,
      });
      await refresh();
      router.replace("/app");
    } catch (error) {
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
      className="absolute inset-y-0 right-0 flex items-center pr-3 text-b2c-text-muted hover:text-b2c-text-secondary"
      aria-label={formData.showPassword ? "Hide password" : "Show password"}
    >
      {formData.showPassword ? <IoIosEyeOff className="h-5 w-5" /> : <IoIosEye className="h-5 w-5" />}
    </button>
  );

  return (
    <AuthShell
      variant="split"
      title="Create your account"
      subtitle="Start practising in a few minutes"
      sidePanel={<AuthQuotePanel />}
    >
      <form className="space-y-5" onSubmit={handleFormSubmission} noValidate>
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
          {isSubmitting ? "Creating your account…" : "Create account"}
        </Button>
      </form>

      <p className={authFooterLink}>
        Already have an account?{" "}
        <Link href="/login" className={authLink}>
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
