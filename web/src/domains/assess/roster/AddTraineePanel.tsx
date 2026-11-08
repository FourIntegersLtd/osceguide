"use client";

import { say } from "@/domains/assess/roster/rosterWords";
import { useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { Note, PasswordFields, h2, hint } from "@/domains/assess/ui";
import { IssuedPassword } from "@/foundation/ui/TemporaryPassword";
import { useTemporaryPassword } from "@/foundation/ui/useTemporaryPassword";
import { rosterErrorMessage } from "@/domains/assess/roster/support";
import { addTrainee, type Cohort } from "@/domains/assess/roster/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { boardBtn, boardPadWide, boardInput, boardLabel } from "@/foundation/ui/boardKit";

/** "Amina Khan" → first "Amina", last "Khan"; one word is a first name. */
export function splitName(value: string): { firstName: string | null; lastName: string | null } {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: null, lastName: null };
  if (parts.length === 1) return { firstName: parts[0] ?? null, lastName: null };
  return {
    firstName: parts.slice(0, -1).join(" "),
    lastName: parts[parts.length - 1] ?? null,
  };
}

/**
 * Add trainees: one at a time, or a spreadsheet.
 *
 * The platform invites an unknown address — the account is created and the
 * person is emailed a link to choose their own password. Where that email cannot
 * be delivered, the admin may type a temporary password for a brand-new account
 * and relay it by hand (changed at first sign-in; never applied to an existing
 * account).
 */
export function AddTraineePanel({
  orgSlug,
  cohorts,
  canManage,
  onAdded,
}: {
  orgSlug: string;
  cohorts: Cohort[];
  canManage: boolean;
  onAdded: () => void;
}) {
  const w = useAssessWords();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [cohortId, setCohortId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const password = useTemporaryPassword();

  const submit = async () => {
    const address = email.trim();
    if (!address) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    password.dismiss();
    try {
      const { firstName, lastName } = splitName(name);
      const trainee = await addTrainee(orgSlug, {
        email: address,
        firstName,
        lastName,
        cohortId: cohortId || null,
        ...(password.typed ? { temporaryPassword: password.typed } : {}),
      });
      const applied = trainee.temporary_password_applied === true;
      setNotice(
        password.typed && !applied
          ? say(w, `${trainee.email} is on the roster. They already had an account, so the password you typed was not used.`)
          : say(w, `${trainee.email} is on the roster.`),
      );
      password.finish(trainee.email, applied);
      setName("");
      setEmail("");
      onAdded();
    } catch (cause) {
      setError(rosterErrorMessage(cause, address, w));
    } finally {
      setBusy(false);
    }
  };

  if (!canManage) {
    return (
      <Note tone="info">
        <b className="block">Only an owner or admin can add {w.trainees}</b>
        {say(w, "Ask one of them to add the people you need on the roster.")}
      </Note>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <form
        className={boardPadWide}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <h2 className={h2}>{say(w, "Add one person")}</h2>
        <p className={cn(t.assessMeta, "m-0")}>
          They are invited by email. If they have no account yet, we create one and send them a link to choose a password. If that email cannot reach them, set a temporary password to relay by hand.
        </p>
        <div>
          <label htmlFor="assess-trainee-name" className={boardLabel}>Full name</label>
          <input id="assess-trainee-name" value={name} onChange={(event) => setName(event.target.value)} className={boardInput} placeholder="e.g. Amina Khan" autoComplete="off" />
        </div>
        <div>
          <label htmlFor="assess-trainee-email" className={boardLabel}>Email address</label>
          <input id="assess-trainee-email" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} className={boardInput} placeholder="amina@hospital.nhs.uk" autoComplete="off" />
        </div>
        <div>
          <label htmlFor="assess-trainee-cohort" className={boardLabel}>{say(w, "Year group (optional)")}</label>
          <select id="assess-trainee-cohort" value={cohortId} onChange={(event) => setCohortId(event.target.value)} className={boardInput}>
            <option value="">{say(w, "No year group")}</option>
            {cohorts.map((cohort) => (
              <option key={cohort.id} value={cohort.id}>
                {cohort.name}
              </option>
            ))}
          </select>
          <div className={hint}>
            {say(w, `An intake, such as "June 2026". Year groups are created under ${w.People} › Groups and year groups.`)}
          </div>
        </div>

        <PasswordFields {...password.field} id="assess-trainee-password" disabled={busy} />

        {error ? <Note tone="bad" role="alert">{error}</Note> : null}
        <button type="submit" className={cn(boardBtn("primary"), "self-start")} disabled={busy || email.trim().length === 0 || !password.ready}>
          {busy ? "Saving…" : `+ Add ${w.trainee}`}
        </button>
      </form>

      {notice ? <Note tone="ok">{notice}</Note> : null}
      {password.issued ? (
        <IssuedPassword email={password.issued.email} password={password.issued.password} onDismiss={password.dismiss} />
      ) : null}
    </div>
  );
}
