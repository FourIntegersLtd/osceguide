"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button, Checkbox, Input, Panel, Textarea } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { readSamlConnection, saveSamlConnection, type SamlConnection } from "@/domains/platform/sso/api";

/**
 * One organisation's SAML identity provider. The read answers "none" until it is saved,
 * which is an empty form; it also gives the two URLs the institution's IdP administrator needs.
 */
export function SamlSection({ slug }: { slug: string }) {
  const state = useAsync(async (signal) => ({ saml: await readSamlConnection(slug, signal) }), [slug]);
  return (
    <Panel
      title="SAML"
      description="For institutions whose identity provider speaks SAML. Save the organisation's SSO arrangement above first, then paste in what their IT team sends."
    >
      <AsyncBoundary state={state}>
        {({ saml }) => <SamlForm key={saml?.id ?? "new"} slug={slug} saml={saml} onSaved={state.reload} />}
      </AsyncBoundary>
    </Panel>
  );
}

function SamlForm({ slug, saml, onSaved }: { slug: string; saml: SamlConnection | null; onSaved: () => void }) {
  const toast = useToast();
  const [entityId, setEntityId] = useState(saml?.idp_entity_id ?? "");
  const [ssoUrl, setSsoUrl] = useState(saml?.idp_sso_url ?? "");
  const [cert, setCert] = useState(saml?.idp_x509_cert ?? "");
  const [emailAttr, setEmailAttr] = useState(saml?.email_attribute ?? "");
  const [enabled, setEnabled] = useState(saml?.enabled ?? false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ready = entityId.trim() !== "" && ssoUrl.trim().startsWith("https://") && cert.trim() !== "";

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      await saveSamlConnection(slug, {
        idp_entity_id: entityId.trim(),
        idp_sso_url: ssoUrl.trim(),
        idp_x509_cert: cert.trim(),
        ...(emailAttr.trim() ? { email_attribute: emailAttr.trim() } : {}),
        enabled,
      });
      toast.success("SAML connection saved");
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-x-6 gap-y-4 md:grid-cols-2">
      {error ? (
        <div className="md:col-span-2">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}
      {saml ? (
        <div className="md:col-span-2">
          <Alert tone="info" title="Give these to the institution's IdP administrator">
            <p>Entity ID: <span className="select-all font-mono">{saml.sp_entity_id}</span></p>
            <p>Reply URL (ACS): <span className="select-all font-mono">{saml.sp_acs_url}</span></p>
            <p>Metadata: <span className="select-all font-mono">{saml.sp_metadata_url}</span></p>
          </Alert>
        </div>
      ) : null}
      <Input label="IdP entity ID" value={entityId} onChange={(e) => setEntityId(e.target.value)} disabled={busy} />
      <Input
        label="IdP sign-in URL"
        value={ssoUrl}
        onChange={(e) => setSsoUrl(e.target.value)}
        disabled={busy}
        placeholder="https://login.microsoftonline.com/…/saml2"
        hint="Must start with https://."
      />
      <div className="md:col-span-2">
        <Textarea
          label="IdP signing certificate"
          value={cert}
          onChange={(e) => setCert(e.target.value)}
          disabled={busy}
          hint="The X.509 certificate from their IdP metadata, as PEM or base64."
        />
      </div>
      <Input
        label="Email attribute"
        value={emailAttr}
        onChange={(e) => setEmailAttr(e.target.value)}
        disabled={busy}
        placeholder="Blank: the Entra email claim"
        hint="The claim that carries the person's email address. Left blank, this and the name claims keep their saved value, or Entra's."
      />
      <div className="flex flex-col gap-3 md:col-span-2">
        <Checkbox
          label="Enabled"
          description="Accept SAML sign-ins for this organisation."
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          disabled={busy}
        />
      </div>
      <div className="flex justify-end md:col-span-2">
        <Button disabled={busy || !ready} onClick={() => void save()}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}
