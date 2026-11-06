"use client";

import Link from "next/link";
import { useState } from "react";
import { boardAlert, boardBtn, boardLabel } from "@/foundation/ui/boardKit";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { AuthShell, AuthButton, AuthFormField } from "@/capabilities/account";
import { sendSiteMessage } from "@/capabilities/help";
import { setupRequestBody } from "@/domains/assess/newOrganisationRequest";

/**
 * What an organisation can use the platform for. Product copy, not data: the
 * backend has no `purpose` column yet, so the choice travels in the request text.
 */
type ProgrammePurpose = "mock_osces" | "formal_exams" | "self_practice" | "recruitment";

const PURPOSES: readonly { id: ProgrammePurpose; label: string }[] = [
  { id: "mock_osces", label: "Mock OSCEs" },
  { id: "formal_exams", label: "Formal exams" },
  { id: "self_practice", label: "Self practice" },
  { id: "recruitment", label: "Recruitment" },
];

const ORG_TYPES = ["Medical school", "Training programme", "Deanery", "Employer"] as const;

function toggled<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((entry) => entry !== value) : [...list, value];
}

/**
 * An institution or employer asking to be set up.
 *
 * An organisation is created by OSCE Guide staff from the platform console
 * (it has a contract and a first admin), so this form files a request through
 * `POST /site/messages`, which staff read in the console inbox and answer by
 * email. It creates no account, so it asks for no password (H-1).
 */
export function NewOrganisation() {
  const [name, setName] = useState("");
  const [orgType, setOrgType] = useState<string>(ORG_TYPES[0]);
  const [purposes, setPurposes] = useState<ProgrammePurpose[]>([]);
  const [ownerName, setOwnerName] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  const purposeMissing = submitted && purposes.length === 0;

  async function send() {
    setSubmitted(true);
    if (purposes.length === 0) return;
    setSending(true);
    setError(null);
    try {
      await sendSiteMessage(
        setupRequestBody({
          name,
          orgType,
          purposes: purposes.map((id) => PURPOSES.find((entry) => entry.id === id)?.label ?? id),
          ownerName,
          email,
          notes,
        }),
      );
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The request could not be sent. Try again.");
    } finally {
      setSending(false);
    }
  }

  if (sent) {
    return (
      <AuthShell
        variant="card"
        lead
        title="Request received"
        subtitle="We will email you at the address you gave once your organisation is ready. Then sign in and the setup assistant takes you through it, step by step."
      >
        <Link href="/login" className={`${boardBtn("primary")} self-start`}>
          Go to sign in
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      variant="card"
      lead
      title="Register your organisation"
      subtitle="Tell us who you are. We set your organisation up and email you a link to sign in, usually within a working day."
    >
      <form
        className="flex flex-col gap-3.5"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <AuthFormField label="Organisation name" name="organisation" required value={name} onChange={(event) => setName(event.target.value)} />
        <AuthFormField
          label="Type"
          name="type"
          fieldType="select"
          options={ORG_TYPES.map((type) => ({ value: type, label: type }))}
          hint="Employer sets you up for hiring: candidates and assessments instead of trainees and sittings."
          value={orgType}
          onChange={(event) => setOrgType(event.target.value)}
        />

        <fieldset className="m-0 min-w-0 border-0 p-0">
          <legend className={`${boardLabel} p-0`}>What you will use it for</legend>
          <div className="flex flex-wrap items-center gap-2.5">
            {PURPOSES.map((purpose) => {
              const on = purposes.includes(purpose.id);
              return (
                <label
                  key={purpose.id}
                  className={`m-0 inline-flex min-h-9 cursor-pointer items-center rounded-full border px-3 text-assess-meta font-normal leading-normal focus-within:ring-4 focus-within:ring-assess-focus-ring ${
                    on
                      ? "border-assess-select-border bg-assess-chip-info-bg text-assess-chip-info-text"
                      : "border-osce-border bg-osce-surface text-osce-ink-900"
                  }`}
                >
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={on}
                    onChange={() => setPurposes((current) => toggled(current, purpose.id))}
                  />
                  {purpose.label}
                </label>
              );
            })}
          </div>
          {purposeMissing ? (
            <p role="alert" className="mt-1.5 text-assess-meta leading-normal text-osce-danger-text">
              Tick at least one.
            </p>
          ) : (
            <p className="mt-1.5 text-assess-meta leading-normal text-osce-ink-500">You can tell us more when we contact you.</p>
          )}
        </fieldset>

        <AuthFormField label="Your name" name="name" autoComplete="name" required value={ownerName} onChange={(event) => setOwnerName(event.target.value)} />
        <AuthFormField label="Work email" name="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <AuthFormField label="Anything else (optional)" name="notes" fieldType="textarea" maxLength={1000} value={notes} onChange={(event) => setNotes(event.target.value)} />
        {error ? <div role="alert" className={boardAlert("bad")}>{error}</div> : null}

        <AuthButton isLoading={sending}>{sending ? "Sending…" : "Request set-up"}</AuthButton>
        <p className={authFooterLink}>
          Already set up?{" "}
          <Link href="/login" className={authLink}>
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
