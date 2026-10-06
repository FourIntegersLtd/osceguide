"use client";

import { useCallback, useState } from "react";
import {
  Alert,
  AsyncBoundary,
  Button,
  Checkbox,
  Input,
  Panel,
  Select,
  Textarea,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  readSsoConfig,
  saveSsoConfig,
  type SsoConfig,
  type SaveSsoConfigInput,
} from "@/domains/platform/api";
import { WriteOnlyNote } from "@/domains/platform/chrome";
import { ssoFieldErrors } from "@/domains/platform/support";

const PROVIDERS = [
  { value: "entra", label: "Microsoft Entra ID" },
  { value: "clerk", label: "Clerk" },
] as const;

interface SsoFormState {
  provider: string;
  issuer: string;
  enabled: boolean;
  sso_only: boolean;
  sign_in_label: string;
  default_exam_code: string;
  hosts: string;
  email_domains: string;
}

const SSO_DESCRIPTION =
  "Single sign-on for this organisation's members. When enabled, the sign-in page shows the organisation's button alongside the password form.";

function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function configToForm(config: SsoConfig | null): SsoFormState {
  if (!config) {
    return {
      provider: "entra",
      issuer: "",
      enabled: false,
      sso_only: false,
      sign_in_label: "",
      default_exam_code: "",
      hosts: "",
      email_domains: "",
    };
  }
  const bindings = config.bindings ?? [];
  return {
    provider: config.provider,
    issuer: config.issuer ?? "",
    enabled: config.enabled,
    sso_only: config.sso_only,
    sign_in_label: config.sign_in_label,
    default_exam_code: config.default_exam_code ?? "",
    hosts: bindings
      .filter((b) => b.kind === "host")
      .map((b) => b.value)
      .join("\n"),
    email_domains: bindings
      .filter((b) => b.kind === "email_domain")
      .map((b) => b.value)
      .join("\n"),
  };
}

/**
 * One organisation's SSO arrangement, read and written by a platform admin.
 *
 * The GET answers `null` when nothing has been set up yet — that is an empty
 * form, not a failure. It is wrapped in `{ config }` because `AsyncBoundary`
 * reads a bare `null` as "not loaded". Every error goes through the boundary,
 * the standard loading/failed gate for a sub-resource section (cf. `MembersSection`).
 */
export function SsoSection({ slug }: { slug: string }) {
  const state = useAsync(
    async (signal) => ({ config: await readSsoConfig(slug, signal) }),
    [slug],
  );

  return (
    <Panel title="SSO" description={SSO_DESCRIPTION}>
      <AsyncBoundary state={state}>
        {({ config }) => (
          <SsoForm slug={slug} config={config} onSaved={state.reload} />
        )}
      </AsyncBoundary>
    </Panel>
  );
}

function SsoForm({
  slug,
  config,
  onSaved,
}: {
  slug: string;
  config: SsoConfig | null;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [form, setForm] = useState<SsoFormState>(() => configToForm(config));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const fieldErrors = submitted ? ssoFieldErrors(form) : {};

  const commit = useCallback(async () => {
    setSubmitted(true);
    if (Object.keys(ssoFieldErrors(form)).length > 0) return;

    setBusy(true);
    setError(null);
    try {
      const body: SaveSsoConfigInput = {
        provider: form.provider,
        issuer: form.issuer.trim() || null,
        enabled: form.enabled,
        sso_only: form.sso_only,
        sign_in_label: form.sign_in_label.trim() || null,
        default_exam_code: form.default_exam_code.trim() || null,
        hosts: linesToList(form.hosts),
        email_domains: linesToList(form.email_domains),
      };
      await saveSsoConfig(slug, body);
      toast.success("SSO configuration saved");
      onSaved();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [form, slug, onSaved, toast]);

  const update = <K extends keyof SsoFormState>(
    key: K,
    value: SsoFormState[K],
  ) => setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <div className="flex max-w-lg flex-col gap-4">
      {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

      {config === null ? (
        <WriteOnlyNote>
          Organisation sign-in (single sign-on) is not set up yet. Fill in the fields below to set it up.
        </WriteOnlyNote>
      ) : null}

      <Select
        label="Provider"
        value={form.provider}
        onChange={(e) => update("provider", e.target.value)}
        disabled={busy}
      >
        {PROVIDERS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
        {PROVIDERS.every((p) => p.value !== form.provider) ? (
          <option value={form.provider}>{form.provider}</option>
        ) : null}
      </Select>

      <Input
        label="Issuer"
        value={form.issuer}
        onChange={(e) => update("issuer", e.target.value)}
        disabled={busy}
        placeholder="https://login.microsoftonline.com/…"
        error={fieldErrors.issuer}
        hint="The sign-in address from the organisation’s identity provider. Their IT team can give you this. Required when organisation sign-in is on."
      />

      <Input
        label="Sign-in label"
        value={form.sign_in_label}
        onChange={(e) => update("sign_in_label", e.target.value)}
        disabled={busy}
        placeholder="Sign in with Kings"
        hint="The button text shown on the sign-in page."
      />

      <Input
        label="Default exam code"
        value={form.default_exam_code}
        onChange={(e) => update("default_exam_code", e.target.value)}
        disabled={busy}
        hint="The exam chosen for new people who join through organisation sign-in. Optional."
      />

      <Textarea
        label="Hosts"
        value={form.hosts}
        onChange={(e) => update("hosts", e.target.value)}
        disabled={busy}
        placeholder="kings.edu"
        hint="One web address per line. People signing in from one of these addresses see the organisation sign-in button."
      />

      <Textarea
        label="Email domains"
        value={form.email_domains}
        onChange={(e) => update("email_domains", e.target.value)}
        disabled={busy}
        placeholder="kings.edu"
        hint="One email domain per line, such as nhs.net. Anyone with a matching email address is offered organisation sign-in."
      />

      <div className="flex flex-col gap-3 border-t border-border pt-4">
        <Checkbox
          label="Enabled"
          description="Show this organisation's sign-in button."
          checked={form.enabled}
          onChange={(e) => update("enabled", e.target.checked)}
          disabled={busy}
        />
        <Checkbox
          label="SSO only"
          description="Hide the email and password form, so members can only use organisation sign-in."
          checked={form.sso_only}
          onChange={(e) => update("sso_only", e.target.checked)}
          disabled={busy}
        />
        {fieldErrors.sso_only ? (
          <p role="alert" className="text-osce-meta text-osce-danger-text">
            {fieldErrors.sso_only}
          </p>
        ) : null}
      </div>

      <div className="flex justify-end">
        <Button disabled={busy} onClick={() => commit()}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}
