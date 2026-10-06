"use client";

import Link from "next/link";
import { useState } from "react";
import { Alert, Button, Checkbox, Input, Select, FoldSection } from "@/foundation/ui";
import { authButtonPrimary, authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { AuthShell } from "@/capabilities/account";

/**
 * What an organisation can use the platform for. Product copy, not data: the
 * backend has no `purpose` column yet, so the ticked choice is not stored.
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

/*
 * The exam list is behind sign-in (`GET /exams` needs a session), and this
 * page is for somebody who has no account, so the four on the canvas are
 * written out. A public sign-up route would bring a public exam list with it.
 */
const EXAMS = ["RCGP SCA", "PLAB 2", "MRCPsych CASC", "Orthopaedic ST3"] as const;

function toggled<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((entry) => entry !== value) : [...list, value];
}

/**
 * An institution setting itself up, without waiting for us to do it.
 *
 * Today an organisation is created by OSCE Guide staff from the platform
 * console; there is no public route that creates one with its first owner.
 * The form is whole and checks what it can, then says it created nothing.
 */
export function NewOrganisation() {
  const [name, setName] = useState("");
  const [orgType, setOrgType] = useState<string>(ORG_TYPES[0]);
  const [exams, setExams] = useState<string[]>([]);
  const [purposes, setPurposes] = useState<ProgrammePurpose[]>([]);
  const [ownerName, setOwnerName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const purposeMissing = submitted && purposes.length === 0;

  return (
    <AuthShell
      variant="card"
      eyebrow="For institutions"
      title="Set up your organisation"
      subtitle="Create a space for your programme. Next you will invite your faculty and trainees, then schedule your first sitting."
    >
      <form
        className="space-y-5"
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(true);
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

        <FoldSection number={2} title="Exams and purpose">
        <div className="space-y-5">
        <fieldset className="space-y-2">
          <legend className="text-osce-meta font-medium text-ink">Exams your trainees prepare for</legend>
          {EXAMS.map((exam) => (
            <Checkbox
              key={exam}
              label={exam}
              checked={exams.includes(exam)}
              onChange={() => setExams((current) => toggled(current, exam))}
            />
          ))}
          <p className="text-osce-caption text-ink-muted">Trainees get these exams in their personal practice too.</p>
        </fieldset>

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
              This decides which features your organisation gets. You can add more later in Settings.
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
        <Input
          label="Password"
          type="password"
          required
          minLength={10}
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          hint="Use 10 or more characters. Or set up single sign-on later in Settings."
        />
        </div>
        </FoldSection>

        {submitted && !purposeMissing ? (
          <Alert tone="warning" title="Nothing was created">
            Self-serve sign-up is not connected yet. Contact us and we will set your organisation up.
          </Alert>
        ) : null}

        <Button type="submit" variant="commit" themeType="b2c" fullWidth size="lg" className={authButtonPrimary}>
          Create organisation
        </Button>
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
