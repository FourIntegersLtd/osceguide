"use client";

import { useState } from "react";
import {
  confirmMfaEnrolmentAtSignIn,
  hasCode,
  startMfaEnrolmentAtSignIn,
  verifyMfaChallenge,
  type components,
  type MfaChallenge,
} from "@/foundation/platform-client";
import { Alert, Input } from "@/foundation/ui";
import AuthButton from "@/capabilities/account/AuthButton";
import { errorMessage } from "@/foundation/hooks";
import { authInput, authLink } from "@/foundation/ui/authTheme";
import { cn } from "@/foundation/ui/cn";
import { AuthenticatorSetup } from "@/capabilities/account/mfa/AuthenticatorSetup";
import { RecoveryCodes } from "@/capabilities/account/mfa/RecoveryCodes";
import {
  isCompleteTotp,
  normaliseRecoveryCode,
  normaliseTotp,
} from "@/capabilities/account/mfa/codes";

type AuthResult = components["schemas"]["AuthResult"];
type Enrolment = components["schemas"]["MfaEnrolmentStart"];

/**
 * The second step of a password sign-in, whichever one the account owes.
 *
 * `mfa_required` asks for a code, or a recovery code for someone without their
 * phone. `mfa_enrolment_required` is an account that policy says must have a
 * second factor and has none yet: it sets one up here, because until it does
 * there is no way in at all.
 *
 * An expired challenge (five minutes) cannot be renewed from here, since
 * renewing it is what the password is for; `onRestart` returns to the form.
 */
export function MfaSignIn({
  challenge,
  onSignedIn,
  onRestart,
}: {
  challenge: MfaChallenge;
  onSignedIn: (result: AuthResult) => void;
  onRestart: () => void;
}) {
  return challenge.status === "mfa_required" ? (
    <MfaCodeStep challengeToken={challenge.challenge_token} onSignedIn={onSignedIn} onRestart={onRestart} />
  ) : (
    <MfaEnrolStep challengeToken={challenge.challenge_token} onSignedIn={onSignedIn} onRestart={onRestart} />
  );
}

/** What to say for a refused step, and whether the challenge is spent. */
function describeFailure(error: unknown): { message: string; expired: boolean } {
  if (hasCode(error, "mfa_challenge_expired")) {
    return { message: "That took too long, so sign in again.", expired: true };
  }
  if (hasCode(error, "invalid_mfa_code")) {
    return { message: "That code is not right. Check the app and try again.", expired: false };
  }
  return { message: errorMessage(error), expired: false };
}

function Expired({ message, onRestart }: { message: string; onRestart: () => void }) {
  return (
    <Alert tone="danger">
      {message}{" "}
      <button type="button" className={authLink} onClick={onRestart}>
        Back to sign in
      </button>
    </Alert>
  );
}

function MfaCodeStep({
  challengeToken,
  onSignedIn,
  onRestart,
}: {
  challengeToken: string;
  onSignedIn: (result: AuthResult) => void;
  onRestart: () => void;
}) {
  const [mode, setMode] = useState<"code" | "recovery">("code");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<{ message: string; expired: boolean } | null>(null);

  const ready = mode === "code" ? isCompleteTotp(value) : normaliseRecoveryCode(value) !== "";

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!ready) return;
    setBusy(true);
    setFailure(null);
    try {
      const result = await verifyMfaChallenge(
        challengeToken,
        mode === "code"
          ? { code: normaliseTotp(value) }
          : { recoveryCode: normaliseRecoveryCode(value) },
      );
      // Leave the button pending: the caller navigates away.
      onSignedIn(result);
    } catch (error) {
      setFailure(describeFailure(error));
      setBusy(false);
    }
  };

  if (failure?.expired) return <Expired message={failure.message} onRestart={onRestart} />;

  return (
    <form className="space-y-5" onSubmit={(event) => void submit(event)} noValidate>
      <p className="text-base text-site-muted">
        {mode === "code"
          ? "Enter the six-digit code from your authenticator app."
          : "Enter one of the recovery codes you saved when you set up two-factor sign-in. Each code works once."}
      </p>
      <Input
        key={mode}
        label={mode === "code" ? "Authentication code" : "Recovery code"}
        name={mode === "code" ? "code" : "recovery_code"}
        placeholder={mode === "code" ? "123 456" : undefined}
        inputMode={mode === "code" ? "numeric" : "text"}
        autoComplete={mode === "code" ? "one-time-code" : "off"}
        // The password form this replaced held focus; without this it falls to
        // the page, and a keyboard user starts again from the top.
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
        value={value}
        onChange={(event) => setValue(event.target.value)}
        error={failure?.message}
        className={cn(authInput, "pl-3.5", mode === "code" && "text-center font-landing-mono text-2xl font-semibold tracking-[0.4em]")}
      />
      <AuthButton isLoading={busy} disabled={!ready}>
        {busy ? "Checking…" : "Continue"}
      </AuthButton>
      <div className="flex flex-col items-center gap-2 text-osce-meta">
        <button
          type="button"
          className={authLink}
          onClick={() => {
            setMode(mode === "code" ? "recovery" : "code");
            setValue("");
            setFailure(null);
          }}
        >
          {mode === "code" ? "Use a recovery code instead" : "Use your authenticator app instead"}
        </button>
        <button type="button" className={authLink} onClick={onRestart}>
          Back to sign in
        </button>
      </div>
    </form>
  );
}

function MfaEnrolStep({
  challengeToken,
  onSignedIn,
  onRestart,
}: {
  challengeToken: string;
  onSignedIn: (result: AuthResult) => void;
  onRestart: () => void;
}) {
  const [enrolment, setEnrolment] = useState<Enrolment | null>(null);
  const [confirmed, setConfirmed] = useState<{ result: AuthResult; codes: string[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<{ message: string; expired: boolean } | null>(null);

  // A click, not a load on mount: starting enrolment writes a pending secret,
  // and a StrictMode double effect would write two.
  const start = async () => {
    setBusy(true);
    setFailure(null);
    try {
      setEnrolment(await startMfaEnrolmentAtSignIn(challengeToken));
    } catch (error) {
      setFailure(describeFailure(error));
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (code: string) => {
    setBusy(true);
    setFailure(null);
    try {
      const result = await confirmMfaEnrolmentAtSignIn(challengeToken, code);
      setConfirmed({ result, codes: result.recovery_codes });
    } catch (error) {
      setFailure(describeFailure(error));
    } finally {
      setBusy(false);
    }
  };

  if (failure?.expired) return <Expired message={failure.message} onRestart={onRestart} />;

  if (confirmed) {
    return (
      <RecoveryCodes
        codes={confirmed.codes}
        doneLabel="Continue"
        onDone={() => onSignedIn(confirmed.result)}
      />
    );
  }

  if (enrolment) {
    return (
      <AuthenticatorSetup
        secret={enrolment.secret}
        otpauthUri={enrolment.otpauth_uri}
        busy={busy}
        error={failure?.message ?? null}
        onConfirm={(code) => void confirm(code)}
      />
    );
  }

  return (
    <div className="space-y-5">
      <p className="text-osce-body text-ink">
        Your account needs two-factor sign-in. Set up an authenticator app on your phone to
        finish signing in. It takes about a minute.
      </p>
      {failure ? <Alert tone="danger">{failure.message}</Alert> : null}
      <AuthButton type="button" isLoading={busy} onClick={() => void start()}>
        Set up an authenticator
      </AuthButton>
      <p className="text-center text-osce-meta">
        <button type="button" className={authLink} onClick={onRestart}>
          Back to sign in
        </button>
      </p>
    </div>
  );
}
