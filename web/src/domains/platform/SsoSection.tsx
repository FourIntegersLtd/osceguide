"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import {
  readSsoConfig,
  saveSsoConfig,
  type SsoConfig,
  type SaveSsoConfigInput,
} from "@/domains/platform/api";
import { Section, WriteOnlyNote } from "@/domains/platform/chrome";

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
    hosts: bindings.filter((b) => b.kind === "host").map((b) => b.value).join("\n"),
    email_domains: bindings.filter((b) => b.kind === "email_domain").map((b) => b.value).join("\n"),
  };
}

/**
 * One organisation's SSO arrangement, read and written by a platform admin.
 *
 * The GET answers `sso_not_configured` when nothing has been set up yet — that
 * is an empty form, not a failure. Every other error goes through
 * `AsyncBoundary`, which is the standard loading/failed/empty gate for a
 * sub-resource section (cf. `MembersSection`).
 */
export function SsoSection({ slug }: { slug: string }) {
  const state = useAsync((signal) => readSsoConfig(slug, signal), [slug]);

  if (hasCode(state.error, "sso_not_configured")) {
    return (
      <Section title="SSO" description="Single sign-on for this organisation's members. When enabled, the sign-in page shows the organisation's button alongside the password form.">
        <SsoForm slug={slug} config={null} onSaved={state.reload} />
      </Section>
    );
  }

  return (
    <Section title="SSO" description="Single sign-on for this organisation's members. When enabled, the sign-in page shows the organisation's button alongside the password form.">
      <AsyncBoundary state={state}>
        {(config) => <SsoForm slug={slug} config={config} onSaved={state.reload} />}
      </AsyncBoundary>
    </Section>
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

  const commit = useCallback(async () => {
    if (form.enabled && !form.issuer.trim()) {
      setError(new Error("SSO cannot be enabled without an issuer."));
      return;
    }
    if (form.sso_only && !form.enabled) {
      setError(new Error("SSO-only sign-in requires SSO to be enabled first."));
      return;
    }

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

  const update = <K extends keyof SsoFormState>(key: K, value: SsoFormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <Card padding="md">
      <div className="flex max-w-lg flex-col gap-4">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

        {config === null ? (
          <WriteOnlyNote>
            SSO is not configured for this organisation yet. Fill in the fields below to set it up.
          </WriteOnlyNote>
        ) : null}

        <label className="flex flex-col gap-1.5">
          <span className="text-osce-meta font-medium text-osce-ink-700">Provider</span>
          <select
            value={form.provider}
            onChange={(e) => update("provider", e.target.value)}
            disabled={busy}
            className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
            {PROVIDERS.every((p) => p.value !== form.provider) ? (
              <option value={form.provider}>{form.provider}</option>
            ) : null}
          </select>
        </label>

        <Input
          label="Issuer"
          value={form.issuer}
          onChange={(e) => update("issuer", e.target.value)}
          disabled={busy}
          placeholder="https://login.microsoftonline.com/…"
          hint="The OIDC issuer URL. Required when SSO is enabled."
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
          hint="Pre-filled for new accounts created through SSO. Optional."
        />

        <label className="flex flex-col gap-1">
          <span className="text-osce-meta font-medium text-osce-ink-700">Hosts</span>
          <textarea
            value={form.hosts}
            onChange={(e) => update("hosts", e.target.value)}
            disabled={busy}
            rows={3}
            placeholder="kings.edu"
            className="w-full rounded-control border border-border-strong bg-surface px-3 py-2 text-sm text-ink"
          />
          <span className="text-osce-meta text-b2c-text-muted">
            One host per line. A sign-in from one of these hosts shows the SSO button.
          </span>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-osce-meta font-medium text-osce-ink-700">Email domains</span>
          <textarea
            value={form.email_domains}
            onChange={(e) => update("email_domains", e.target.value)}
            disabled={busy}
            rows={3}
            placeholder="kings.edu"
            className="w-full rounded-control border border-border-strong bg-surface px-3 py-2 text-sm text-ink"
          />
          <span className="text-osce-meta text-b2c-text-muted">
            One domain per line. A user whose email matches one of these is offered SSO.
          </span>
        </label>

        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => update("enabled", e.target.checked)}
              disabled={busy}
              className="h-4 w-4 rounded border-border-strong"
            />
            <span className="text-sm text-ink">Enabled</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.sso_only}
              onChange={(e) => update("sso_only", e.target.checked)}
              disabled={busy}
              className="h-4 w-4 rounded border-border-strong"
            />
            <span className="text-sm text-ink">
              SSO only — hide the password form entirely
            </span>
          </label>
        </div>

        <div className="flex justify-end">
          <Button disabled={busy} onClick={() => void commit()}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
