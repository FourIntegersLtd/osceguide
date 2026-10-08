"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Input, Panel } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { formatLongDateTime } from "@/foundation/format";
import { issueScimToken, listScimTokens, revokeScimToken, type ScimTokenIssued } from "@/domains/assess/api";

/**
 * The connectors that provision this organisation's people from its identity provider.
 *
 * A token is shown once, when it is made: the list afterwards holds only its first characters.
 * Revoking one refuses its connector from the next request.
 */
export function ScimTokens({ orgSlug }: { orgSlug: string }) {
  const tokens = useAsync((signal) => listScimTokens(orgSlug, signal), [orgSlug]);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [issued, setIssued] = useState<ScimTokenIssued | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function act(action: () => Promise<void>) {
    setBusy(true);
    setFailure(null);
    setIssued(null);
    try {
      await action();
      tokens.reload();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title="Provisioning"
      description="Let your identity provider add and remove people here. Give each connector its own token."
    >
      <div className="flex max-w-xl flex-col gap-4">
        {failure ? <Alert tone="danger">{failure}</Alert> : null}
        {issued ? (
          <Alert tone="warning">
            Copy this token now; it cannot be shown again. <code className="break-all">{issued.token}</code>{" "}
            <Button variant="secondary" size="sm" onClick={() => setIssued(null)}>
              Dismiss
            </Button>
          </Alert>
        ) : null}
        <form
          className="flex items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!label.trim()) return;
            void act(async () => {
              setIssued(await issueScimToken(orgSlug, label.trim()));
              setLabel("");
            });
          }}
        >
          <Input label="Connector name" value={label} onChange={(event) => setLabel(event.target.value)} />
          <Button type="submit" disabled={busy || !label.trim()}>
            Create token
          </Button>
        </form>
        <AsyncBoundary state={tokens}>
          {(items) =>
            items.length === 0 ? (
              <p className="text-osce-body text-b2b-mid">No tokens yet.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {items.map((token) => (
                  <li key={token.id} className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-osce-body font-medium text-b2b-headline">{token.label}</p>
                      <p className="text-osce-meta text-b2b-mid">
                        {token.token_prefix}… · {token.last_used_at ? `last used ${formatLongDateTime(token.last_used_at)}` : "never used"}
                      </p>
                    </div>
                    {token.revoked_at ? (
                      <Badge variant="neutral">Revoked</Badge>
                    ) : (
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={busy}
                        onClick={() => void act(() => revokeScimToken(orgSlug, token.id))}
                      >
                        Revoke
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            )
          }
        </AsyncBoundary>
      </div>
    </Panel>
  );
}
