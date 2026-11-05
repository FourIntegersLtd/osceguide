"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Checkbox, Input, Select, Textarea } from "@/foundation/ui";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { AuthShell, AuthButton } from "@/capabilities/account";
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
        icon="done"
        title="Request received"
        subtitle="We will email you at the address you gave once your organisation is ready. Then sign in and the setup assistant takes you through it, step by step."
      >
        <p className={authFooterLink}>
          <Link href="/login" className={authLink}>
            Go to sign in
          </Link>
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      variant="card"
      wide
      icon="building"
      title="Register your organisation"
      subtitle="Tell us who you are. We set your organisation up and email you a link to sign in, usually within a working day."
    >
      <form
        className="space-y-5"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <Input label="Organisation name" required value={name} onChange={(event) => setName(event.target.value)} />
        <Select
          label="Type"
          hint="Employer sets you up for hiring: candidates and assessments instead of trainees and sittings."
          value={orgType}
          onChange={(event) => setOrgType(event.target.value)}
        >
          {ORG_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </Select>

        <fieldset className="space-y-2">
          <legend className="text-osce-meta font-medium text-ink">What you will use it for</legend>
          {PURPOSES.map((purpose) => (
            <Checkbox
              key={purpose.id}
              label={purpose.label}
              checked={purposes.includes(purpose.id)}
              onChange={() => setPurposes((current) => toggled(current, purpose.id))}
            />
          ))}
          {purposeMissing ? (
            <p role="alert" className="text-osce-meta text-danger">
              Tick at least one.
            </p>
          ) : (
            <p className="text-osce-caption text-ink-muted">You can tell us more when we contact you.</p>
          )}
        </fieldset>

        <Input
          label="Your name"
          required
          autoComplete="name"
          value={ownerName}
          onChange={(event) => setOwnerName(event.target.value)}
        />
        <Input
          label="Work email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Textarea
          label="Anything else (optional)"
          maxLength={1000}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
        {error ? <Alert tone="danger">{error}</Alert> : null}

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
