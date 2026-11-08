"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert } from "@/foundation/ui";
import { boardBtn } from "@/foundation/ui/boardKit";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { AuthShell, AuthButton, AuthFormField } from "@/capabilities/account";
import { sendSiteMessage } from "@/capabilities/help";
import {
  EMPLOYER_REGISTER,
  REGISTER_PATHS,
  employerRequestBody,
  type RegisterPath,
} from "@/domains/assess/newOrganisationRequest";

/** "A school or deanery / An employer": which request the page files. */
export function RegisterPathPills({ value, onChange }: { value: RegisterPath; onChange: (path: RegisterPath) => void }) {
  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="sr-only">What are you setting up?</legend>
      <div className="flex flex-wrap items-center gap-2.5">
        {REGISTER_PATHS.map((path) => (
          <label
            key={path.id}
            className={`m-0 inline-flex min-h-9 cursor-pointer items-center rounded-full border px-3 text-assess-meta font-normal leading-normal focus-within:ring-4 focus-within:ring-assess-focus-ring ${
              value === path.id
                ? "border-assess-select-border bg-assess-chip-info-bg text-assess-chip-info-text"
                : "border-osce-border bg-osce-surface text-osce-ink-900"
            }`}
          >
            <input type="radio" name="register-path" className="sr-only" checked={value === path.id} onChange={() => onChange(path.id)} />
            {path.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/**
 * An employer asking to be set up (HireRegister). Staff create the organisation with `org_type: employer`; this files
 * the request through `POST /site/messages` and creates no account, so it asks for no password.
 */
export function NewEmployer({ pills }: { pills: React.ReactNode }) {
  const [name, setName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [email, setEmail] = useState("");
  const [volume, setVolume] = useState("");
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(false);
  const [sent, setSent] = useState(false);
  const copy = EMPLOYER_REGISTER;

  async function send() {
    setSending(true);
    setFailed(false);
    try {
      await sendSiteMessage(employerRequestBody({ name, ownerName, email, candidatesPerYear: volume }));
      setSent(true);
    } catch {
      setFailed(true);
    } finally {
      setSending(false);
    }
  }

  if (sent) {
    const done = copy.sent(name, email);
    return (
      <AuthShell variant="card" lead title={done.title} subtitle={done.body}>
        <p className="m-0 text-assess-desc font-semibold">{done.heading}</p>
        <Link href="/login" className={`${boardBtn("primary")} self-start`}>
          {done.link}
        </Link>
      </AuthShell>
    );
  }

  return (
    <AuthShell variant="card" lead title={copy.title} subtitle={`${copy.subtitle}`}>
      <form
        className="flex flex-col gap-3.5"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        {pills}
        <p className="m-0 text-assess-meta leading-normal text-osce-ink-500">{copy.hint}</p>
        <AuthFormField label="Organisation name" name="organisation" required value={name} onChange={(event) => setName(event.target.value)} />
        <AuthFormField label="Your name" name="name" autoComplete="name" required value={ownerName} onChange={(event) => setOwnerName(event.target.value)} />
        <AuthFormField label="Work email" name="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
        <AuthFormField label="How many candidates a year?" name="candidates" maxLength={40} value={volume} onChange={(event) => setVolume(event.target.value)} />
        {failed ? (
          <Alert tone="danger" title={copy.failed.title}>
            {copy.failed.body}
          </Alert>
        ) : null}
        <AuthButton isLoading={sending}>{sending ? "Sending…" : copy.send}</AuthButton>
        <p className={authFooterLink}>
          Already have an account?{" "}
          <Link href="/login" className={authLink}>
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
