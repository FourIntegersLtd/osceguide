"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type ChangeEvent } from "react";
import { IoIosEye, IoIosEyeOff } from "react-icons/io";
import { Alert } from "@/foundation/ui";
import { hasCode, login, type components, type MfaChallenge } from "@/foundation/platform-client";
import { examAuthHref, normalizeExamCode } from "@/foundation/session/examSelection";
import { PERSONAL_SLUG } from "@/foundation/routing/workspace";
import { can, useSession } from "@/foundation/session";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthButton from "@/capabilities/account/AuthButton";
import AuthFormField from "@/capabilities/account/AuthFormField";
import AuthQuotePanel from "@/capabilities/account/AuthQuotePanel";
import { readSsoSignIn, startSsoSignIn, type SsoSignIn } from "@/capabilities/account/api";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { lastSessionUser, nextAfterSignIn } from "@/foundation/session/sessionUser";
import {
  loginSchema,
  validateWith,
  type FieldErrors,
} from "@/capabilities/account/support/validateAuthForm";
import { mapAuthApiError } from "@/capabilities/account/support/mapAuthApiError";
import { readAuthNotice, type AuthNoticeTone } from "@/capabilities/account/support/authNotices";
import { MfaSignIn } from "@/capabilities/account/mfa/MfaSignIn";
import { ssoForRefusedPassword } from "@/capabilities/account/support/ssoDiscovery";

type AuthResult = components["schemas"]["AuthResult"];

type LoginField = "email" | "password";

function noticeTone(tone: AuthNoticeTone): "info" | "success" | "danger" {
  if (tone === "error") return "danger";
  return tone;
}

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
 * is an entitlement, not something to choose at the door).
 *
 * The SSO button is back, and it is the backend's answer now rather than a
 * hostname allow-list in the bundle: on mount this asks
 * `GET /auth/sso/sign-in?host=<this host>`, which names the organisation and
 * says whether to draw the password form at all. A host nobody has claimed
 * answers `null` and the page is the ordinary password form. **`sso_only` is a
 * display rule here** — it hides the password form. The refusal is the
 * backend's: an SSO-only account has `password_login_disabled` set. The door itself works: the button
 * follows `POST /auth/sso/login`'s `sign_in_url` out and `/auth/sso/callback`
 * completes the return. What has no screen yet is the *other* half — claiming
 * a host for an organisation (`GET`/`PUT /platform/orgs/{slug}/sso` are
 * served and called by nothing).
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
  const [sso, setSso] = useState<SsoSignIn | null>(null);
  // Why the organisation's button did not take them somewhere: the broker may
  // be unconfigured, or the arrangement switched off since discovery answered.
  const [ssoNotice, setSsoNotice] = useState<string | null>(null);
  const [ssoBusy, setSsoBusy] = useState(false);
  // Why the password form gave way to the organisation's button.
  const [ssoReason, setSsoReason] = useState<string | null>(null);
  // The second step an account owes after a right password (E-11). While it
  // is set the page is that step, not the password form.
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  const arrivalNotice = readAuthNotice(new URLSearchParams(searchParams.toString()));

  /*
   * Discovery, once, on the host the visitor actually arrived at. It is a
   * display concern and must never block or delay the password form, so a
   * `null` answer or a failed request simply leaves the ordinary sign-in
   * standing. A member it missed is caught on submit instead: see
   * `ssoForRefusedPassword`.
   */
  useEffect(() => {
    let cancelled = false;
    const host = typeof window === "undefined" ? undefined : window.location.hostname;
    if (!host) return;
    readSsoSignIn({ host })
      .then((result) => {
        if (!cancelled) setSso(result);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const showPasswordForm = !sso?.sso_only;

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
      const outcome = await login(result.data.email, result.data.password);
      if (outcome.status === "signed_in") {
        // Leaves the button pending: `land` moves the page on.
        await land(outcome);
        return;
      }
      setChallenge(outcome);
    } catch (error) {
      if (hasCode(error, "password_login_disabled")) {
        // The account signs in through its organisation. Find that door by
        // email, since the host lookup on arrival may have missed it.
        const found = await ssoForRefusedPassword(result.data.email, readSsoSignIn);
        if (found.sso) setSso(found.sso);
        setSsoReason(found.sso ? found.notice : null);
        setFormError(found.sso ? null : found.notice);
      } else {
        const mapped = mapAuthApiError<LoginField>(
          error,
          "We couldn't sign you in. Check your details and try again.",
        );
        setFormError(mapped.formError);
        setFieldErrors(mapped.fieldErrors);
      }
    }
    setIsSubmitting(false);
  };

  // Keep the button pending; the page is about to change. Platform staff land
  // on their console; everyone else goes to `/app`, which decides which
  // workspace from where they were last.
  const land = async (authenticated: AuthResult) => {
    // Read before `refresh`, which records the person now signing in.
    const previousUser = lastSessionUser();
    const session = await refresh();
    const returnTo = nextAfterSignIn(searchParams, previousUser, authenticated.user.id);
    // The staff layout's and `/app`'s check, read off the session `refresh` just loaded.
    const landing = can(session, "administer_platform")
      ? "/staff"
      : examCode
        ? `/app/${PERSONAL_SLUG}`
        : "/app";
    router.replace(returnTo ?? landing);
  };

  if (challenge) {
    return (
      <AuthShell
        variant="split"
        icon="shield"
        title="Two-factor sign-in"
        subtitle={
          challenge.status === "mfa_required"
            ? "One more step to confirm it is you"
            : "This account requires a second factor"
        }
        sidePanel={<AuthQuotePanel />}
      >
        <MfaSignIn
          challenge={challenge}
          onSignedIn={(authenticated) => void land(authenticated)}
          onRestart={() => {
            setChallenge(null);
            setFormData((prev) => ({ ...prev, password: "" }));
          }}
        />
      </AuthShell>
    );
  }

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
      className="absolute inset-y-0 right-0 flex items-center pr-3 text-ink-subtle hover:text-ink-muted"
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
      {arrivalNotice ? (
        <Alert tone={noticeTone(arrivalNotice.tone)} className="mb-4">
          {arrivalNotice.message}
        </Alert>
      ) : null}
      {showPasswordForm && (
        <form className="space-y-5" method="post" onSubmit={handleFormSubmission} noValidate>
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
          <AuthButton isLoading={isSubmitting}>
            {isSubmitting ? "Signing you in…" : "Sign in"}
          </AuthButton>
        </form>
      )}

      {showPasswordForm && (
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
      )}

      {sso ? (
        <div className="space-y-3">
          {ssoReason ? <Alert tone="info">{ssoReason}</Alert> : null}
          {/*
           * The organisation's own wording, from the discovery answer.
           *
           * This used to open a notice saying organisation sign-in was not
           * available, because `POST /auth/sso/login` did not exist yet. It
           * does: the backend returns the broker's URL and tells the broker to
           * come back to `/auth/sso/callback`, which posts the token it was
           * handed and adopts the session. So the button is now the door it
           * always looked like.
           */}
          <AuthButton
            type="button"
            variant={showPasswordForm ? "line" : "brand"}
            disabled={ssoBusy}
            onClick={() => {
              setSsoBusy(true);
              setSsoNotice(null);
              void startSsoSignIn(sso.org_slug)
                // A whole-page navigation: the person is leaving for the
                // identity provider and returning with none of this page's
                // state intact, so a client route would be a lie.
                .then((url) => window.location.assign(url))
                // Stay put and say why. On a host that still shows the password
                // form the reader has a way in; on an `sso_only` host the notice
                // below points at support. Either way a silent no-op is worse.
                .catch((cause: unknown) => {
                  setSsoBusy(false);
                  setSsoNotice(
                    cause instanceof Error
                      ? cause.message
                      : "We could not reach your organisation's sign-in.",
                  );
                });
            }}
          >
            {ssoBusy ? "Opening sign-in…" : sso.sign_in_label}
          </AuthButton>
          {ssoNotice ? (
            <p role="alert" className="text-center text-osce-meta text-osce-danger">
              {ssoNotice}
            </p>
          ) : null}
          {!showPasswordForm ? (
            <p className={authFooterLink}>
              Sign in with your organisation account. Password sign-in
              isn&apos;t available on this site. Need help?{" "}
              <a href={`mailto:${SUPPORT_EMAIL}`} className={authLink}>
                Contact support
              </a>
              .
            </p>
          ) : null}
        </div>
      ) : null}
    </AuthShell>
  );
}
