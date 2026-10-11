"use client";

import { useState } from "react";
import { HiOutlineCheckCircle, HiOutlineShieldCheck } from "react-icons/hi2";
import { hasCode } from "@/foundation/platform-client";
import { AsyncBoundary, Button, ConfirmModal, Input, Modal, Panel } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  confirmMyMfa,
  disableMyMfa,
  readMyMfa,
  regenerateRecoveryCodes,
  startMyMfaEnrolment,
  type MfaEnrolment,
  type MfaStatus,
} from "@/capabilities/account/api";
import { AuthenticatorSetup } from "@/capabilities/account/mfa/AuthenticatorSetup";
import { RecoveryCodes } from "@/capabilities/account/mfa/RecoveryCodes";
import { isCompleteTotp, normaliseTotp } from "@/capabilities/account/mfa/codes";
import { settingsMeta, settingsSub } from "@/capabilities/account/settings/SettingsKit";

/** Which dialog is open. Each one needs a current code, so each is its own step. */
type Dialog =
  | { kind: "enrol"; enrolment: MfaEnrolment }
  | { kind: "codes"; codes: string[] }
  | { kind: "regenerate" }
  | { kind: "disable" }
  | { kind: "confirmOff"; code: string };

const REQUIRED_BECAUSE: Record<NonNullable<MfaStatus["required_reason"]>, string> = {
  platform_admin: "Staff accounts must use two-factor sign-in.",
  org_policy: "Your organisation requires two-factor sign-in for its staff.",
};

function codeFailure(error: unknown): string {
  if (hasCode(error, "invalid_mfa_code")) return "That code is not right. Check the app and try again.";
  if (hasCode(error, "mfa_required_by_policy")) {
    return "Two-factor sign-in is required for this account, so it cannot be turned off.";
  }
  return errorMessage(error);
}

/**
 * Two-factor sign-in, from Settings (E-11).
 *
 * The state is the server's (`GET /me/mfa`): whether an authenticator is set
 * up, whether policy requires one and why, and how many recovery codes are
 * left. Turning it off is offered only where it is not required, and the
 * server refuses it there anyway.
 */
export function TwoFactorPanel() {
  const status = useAsync((signal) => readMyMfa(signal), []);
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [offError, setOffError] = useState<string | null>(null);
  const toast = useToast();

  const start = async () => {
    setStarting(true);
    setStartError(null);
    try {
      setDialog({ kind: "enrol", enrolment: await startMyMfaEnrolment() });
    } catch (error) {
      setStartError(errorMessage(error));
    } finally {
      setStarting(false);
    }
  };

  const close = () => {
    setDialog(null);
    status.reload();
  };

  const turnOff = async (code: string) => {
    setOffError(null);
    try {
      await disableMyMfa(code);
      toast.success("Two-factor sign-in is off");
      close();
    } catch (cause) {
      if (hasCode(cause, "invalid_mfa_code")) {
        // The confirm step has no code field: send them back to the one that does.
        toast.error(codeFailure(cause));
        setDialog({ kind: "disable" });
      } else {
        setOffError(codeFailure(cause));
      }
    }
  };

  return (
    <>
      <Panel
        title="Two-factor sign-in"
        description="Ask for a code from your authenticator app at every sign-in"
      >
        <AsyncBoundary state={status}>
          {(mfa: MfaStatus) => (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0 flex-1 space-y-1">
                {mfa.enabled ? (
                  <>
                    <p className="flex items-center gap-1.5 text-osce-body font-medium text-success">
                      <HiOutlineCheckCircle className="h-5 w-5" aria-hidden />
                      Enabled
                    </p>
                    <p className={settingsSub}>
                      You sign in with your password and a code from your authenticator app.{" "}
                      {mfa.recovery_codes_remaining} recovery{" "}
                      {mfa.recovery_codes_remaining === 1 ? "code" : "codes"} left.
                    </p>
                  </>
                ) : (
                  <p className={settingsSub}>Add a code from an authenticator app when you sign in.</p>
                )}
                {mfa.required && mfa.required_reason ? (
                  <p className={settingsMeta}>{REQUIRED_BECAUSE[mfa.required_reason]}</p>
                ) : null}
                {startError ? (
                  <p role="alert" className="text-osce-meta text-danger">
                    {startError}
                  </p>
                ) : null}
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {mfa.enabled ? (
                  <>
                    <Button variant="secondary" onClick={() => setDialog({ kind: "regenerate" })}>
                      New recovery codes
                    </Button>
                    {!mfa.required ? (
                      <Button variant="secondary" onClick={() => setDialog({ kind: "disable" })}>
                        Turn off
                      </Button>
                    ) : null}
                  </>
                ) : (
                  <Button variant="secondary" disabled={starting} onClick={() => start()} className="gap-2">
                    <HiOutlineShieldCheck className="h-4 w-4" aria-hidden />
                    {starting ? "Starting…" : "Set up"}
                  </Button>
                )}
              </div>
            </div>
          )}
        </AsyncBoundary>
      </Panel>

      <ConfirmModal
        isOpen={dialog?.kind === "confirmOff"}
        onCancel={close}
        onConfirm={() => (dialog?.kind === "confirmOff" ? turnOff(dialog.code) : undefined)}
        title="Turn off two-factor sign-in?"
        message="You will sign in with your password alone. Your recovery codes stop working."
        confirmText="Turn off"
        cancelText="Keep it on"
        tone="danger"
        error={offError}
      />

      {dialog && dialog.kind !== "confirmOff" ? (
        <Modal width="440px" title={DIALOG_TITLES[dialog.kind]} onClose={close}>
          <div className="p-5">
            {/* The modal's own title is for screen readers only. */}
            <h3 className="mb-4 font-heading text-osce-subheading font-semibold text-ink" aria-hidden>
              {DIALOG_TITLES[dialog.kind]}
            </h3>
            {dialog.kind === "enrol" ? (
              <EnrolDialog
                enrolment={dialog.enrolment}
                onConfirmed={(codes) => setDialog({ kind: "codes", codes })}
              />
            ) : dialog.kind === "codes" ? (
              <RecoveryCodes codes={dialog.codes} doneLabel="Done" onDone={close} />
            ) : dialog.kind === "regenerate" ? (
              <CodeDialog
                description="Your current recovery codes stop working as soon as new ones are made."
                action="Make new codes"
                run={regenerateRecoveryCodes}
                onDone={(codes) => setDialog({ kind: "codes", codes })}
              />
            ) : (
              <CodeDialog
                description="Enter a code from your authenticator app to continue."
                action="Continue"
                run={async (code) => [code]}
                onDone={([code]) => {
                  setOffError(null);
                  setDialog({ kind: "confirmOff", code: code ?? "" });
                }}
              />
            )}
          </div>
        </Modal>
      ) : null}
    </>
  );
}

const DIALOG_TITLES: Record<Exclude<Dialog["kind"], "confirmOff">, string> = {
  enrol: "Set up two-factor sign-in",
  codes: "Your recovery codes",
  regenerate: "New recovery codes",
  disable: "Turn off two-factor sign-in",
};

function EnrolDialog({
  enrolment,
  onConfirmed,
}: {
  enrolment: MfaEnrolment;
  onConfirmed: (codes: string[]) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <AuthenticatorSetup
      secret={enrolment.secret}
      otpauthUri={enrolment.otpauth_uri}
      busy={busy}
      error={error}
      onConfirm={(code) => {
        setBusy(true);
        setError(null);
        confirmMyMfa(code)
          .then(onConfirmed)
          .catch((cause: unknown) => {
            setError(codeFailure(cause));
            setBusy(false);
          });
      }}
    />
  );
}

/** A change to an existing authenticator, proven with a current code. */
function CodeDialog({
  description,
  action,
  run,
  onDone,
}: {
  description: string;
  action: string;
  run: (code: string) => Promise<string[]>;
  onDone: (codes: string[]) => void;
}) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="space-y-4"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (!isCompleteTotp(code)) return;
        setBusy(true);
        setError(null);
        run(normaliseTotp(code))
          .then(onDone)
          .catch((cause: unknown) => {
            setError(codeFailure(cause));
            setBusy(false);
          });
      }}
    >
      <p className="text-osce-body text-ink">{description}</p>
      <Input
        label="Code from your authenticator app"
        name="code"
        inputMode="numeric"
        autoComplete="one-time-code"
        // The dialog's only field: opening a dialog moves focus into it.
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
        value={code}
        onChange={(event) => setCode(event.target.value)}
        error={error}
      />
      <Button type="submit" fullWidth isLoading={busy} disabled={!isCompleteTotp(code)}>
        {action}
      </Button>
    </form>
  );
}
