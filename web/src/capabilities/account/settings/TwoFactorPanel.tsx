"use client";

import { useState } from "react";
import { HiOutlineCheckCircle, HiOutlineShieldCheck } from "react-icons/hi2";
import { hasCode } from "@/foundation/platform-client";
import { AsyncBoundary, Button, Input, Modal } from "@/foundation/ui";
import { AccountButton, AccountCard, useBoardSkin } from "@/capabilities/account/settings/AccountKit";
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
  | { kind: "disable" };

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
  const toast = useToast();
  const board = useBoardSkin();

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

  return (
    <>
      <AccountCard title="Two-factor sign-in" description="Ask for a code from your authenticator app at every sign-in">
        <AsyncBoundary state={status}>
          {(mfa: MfaStatus) => (
            <div className={board ? "flex flex-wrap items-center gap-3 py-4" : "flex flex-wrap items-center justify-between gap-3"}>
              <div className={board ? "min-w-0 flex-1 text-assess-label text-ink" : "min-w-0 flex-1 space-y-1"}>
                {mfa.enabled ? (
                  board ? (
                    <p className="m-0">
                      <b className="font-semibold text-osce-success-text">{"\u2713"} Enabled</b> You sign in with your password and a code from your authenticator app.{" "}
                      {mfa.recovery_codes_remaining} recovery {mfa.recovery_codes_remaining === 1 ? "code" : "codes"} left.
                    </p>
                  ) : (
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
                  )
                ) : (
                  <p className={board ? "m-0" : settingsSub}>Add a code from an authenticator app when you sign in.</p>
                )}
                {mfa.required && mfa.required_reason ? (
                  <p className={board ? "m-0 text-assess-meta text-ink-muted" : settingsMeta}>{REQUIRED_BECAUSE[mfa.required_reason]}</p>
                ) : null}
                {startError ? (
                  <p role="alert" className={board ? "m-0 text-assess-meta text-osce-danger-text" : "text-osce-meta text-danger"}>
                    {startError}
                  </p>
                ) : null}
              </div>
              <div className="flex shrink-0 flex-wrap gap-2">
                {mfa.enabled ? (
                  <>
                    <AccountButton variant="secondary" small onClick={() => setDialog({ kind: "regenerate" })}>
                      New recovery codes
                    </AccountButton>
                    {!mfa.required ? (
                      <AccountButton variant="secondary" small onClick={() => setDialog({ kind: "disable" })}>
                        Turn off
                      </AccountButton>
                    ) : null}
                  </>
                ) : (
                  <AccountButton variant="secondary" icon={HiOutlineShieldCheck} disabled={starting} onClick={() => start()}>
                    {starting ? "Starting…" : "Set up"}
                  </AccountButton>
                )}
              </div>
            </div>
          )}
        </AsyncBoundary>
      </AccountCard>

      {dialog ? (
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
                description="Your old recovery codes will stop working. Save the new ones somewhere safe."
                action="Make new codes"
                run={regenerateRecoveryCodes}
                onDone={(codes) => setDialog({ kind: "codes", codes })}
              />
            ) : (
              <CodeDialog
                description="You will sign in with your password alone. Your recovery codes stop working. Enter a code from your authenticator app to continue."
                action="Turn off"
                run={async (code) => {
                  await disableMyMfa(code);
                  return [];
                }}
                onDone={() => {
                  toast.success("Two-factor sign-in is off");
                  close();
                }}
                onCancel={close}
              />
            )}
          </div>
        </Modal>
      ) : null}
    </>
  );
}

const DIALOG_TITLES: Record<Dialog["kind"], string> = {
  enrol: "Set up two-factor sign-in",
  codes: "Your recovery codes",
  regenerate: "New recovery codes",
  disable: "Turn off two-factor sign-in?",
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
  onCancel,
}: {
  description: string;
  action: string;
  run: (code: string) => Promise<string[]>;
  onDone: (codes: string[], code: string) => void;
  onCancel?: () => void;
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
        const typed = normaliseTotp(code);
        run(typed)
          .then((codes) => onDone(codes, typed))
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
      <div className="flex gap-2">
        {onCancel ? (
          <Button type="button" variant="secondary" fullWidth onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
        <Button type="submit" fullWidth isLoading={busy} disabled={!isCompleteTotp(code)}>
          {action}
        </Button>
      </div>
    </form>
  );
}
