"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Checkbox, Input, Select, Textarea, FoldSection } from "@/foundation/ui";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { AuthShell, AuthButton } from "@/capabilities/account";
import { sendSiteMessage } from "@/capabilities/help";
import { setupRequestBody } from "@/domains/assess/newOrganisationRequest";

/**
 * What an organisation can use the platform for. Product copy, not data: the
 * backend has no `purpose` column yet, so the choice travels in the request text.
 */
type ProgrammePurpose = "exam_preparation" | "placement" | "recruitment" | "onboarding" | "cpd";

const PURPOSES: readonly { id: ProgrammePurpose; label: string }[] = [
  { id: "exam_preparation", label: "Exam preparation" },
  { id: "placement", label: "Placement preparation" },
  { id: "recruitment", label: "Recruitment" },
  { id: "onboarding", label: "Onboarding" },
  { id: "cpd", label: "Continuous development" },
];

const ORG_TYPES = ["Training programme", "Medical school", "Deanery", "Employer"] as const;

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
        eyebrow="For institutions"
        title="Request received"
        subtitle={`Thank you. We will set up ${name} and email ${email} with the next steps, usually within one working day.`}
      >
        <p className={authFooterLink}>
          <Link href="/login" className={authLink}>
            Back to sign in
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
      eyebrow="For institutions"
      title="Set up your organisation"
      subtitle="Tell us about your programme or team. We create your organisation and make you its first admin, then you invite your faculty and trainees."
    >
      <form
        className="space-y-5"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <FoldSection number={1} title="Organisation">
        <div className="space-y-5">
        <Input label="Organisation name" required value={name} onChange={(event) => setName(event.target.value)} />
        <Select label="Type" value={orgType} onChange={(event) => setOrgType(event.target.value)}>
          {ORG_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </Select>
        </div>
        </FoldSection>

        <FoldSection number={2} title="Purpose">
        <div className="space-y-5">
        <fieldset className="space-y-2">
          <legend className="text-osce-meta font-medium text-ink">What will you use OSCE Guide for?</legend>
          <p className="text-osce-caption text-ink-muted">Tick at least one.</p>
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
            <p className="text-osce-caption text-ink-muted">
              This decides which features your organisation gets. To change it later, contact support.
            </p>
          )}
        </fieldset>
        </div>
        </FoldSection>

        <FoldSection number={3} title="Your account">
        <div className="space-y-5">
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
          label="Notes (optional)"
          hint="Anything we should know, such as cohort size, timelines or the exams you run."
          maxLength={1000}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
        </div>
        </FoldSection>

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
