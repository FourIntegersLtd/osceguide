"use client";

import { useState } from "react";
import { AsyncBoundary, b2bTokens as t, cn } from "@/foundation/ui";
import { card, Chip, Note, row } from "@/domains/assess/ui";
import { SettingsCard } from "@/domains/assess/settings/SettingsCard";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { formatLongDateTime } from "@/foundation/format";
import { issueScimToken, listScimTokens, revokeScimToken, type ScimTokenIssued } from "@/domains/assess/api";
import { boardBtn, boardInput, boardButtonSmall } from "@/foundation/ui/boardKit";

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
    <SettingsCard title="Provisioning" lead="Let your identity provider add and remove people here. Give each connector its own token.">
      {failure ? <Note tone="bad" role="alert">{failure}</Note> : null}
      {issued ? (
        <Note tone="warn">
          Copy this token now; it cannot be shown again. <code className="break-all">{issued.token}</code>{" "}
          <button type="button" className={boardButtonSmall} onClick={() => setIssued(null)}>
            Dismiss
          </button>
        </Note>
      ) : null}
      <form
        className="flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!label.trim()) return;
          void act(async () => {
            setIssued(await issueScimToken(orgSlug, label.trim()));
            setLabel("");
          });
        }}
      >
        <input
          aria-label="Connector name"
          className={cn(boardInput, "min-w-0 flex-[1_1_240px]")}
          placeholder="Connector name"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
        />
        <button type="submit" className={boardBtn("primary")} disabled={busy || !label.trim()}>
          Create token
        </button>
      </form>
      <AsyncBoundary state={tokens}>
        {(items) =>
          items.length === 0 ? (
            <p className={cn(t.assessMeta, "m-0")}>No tokens yet.</p>
          ) : (
            <div className={card}>
              {items.map((token, index) => (
                <div key={token.id} className={cn(row, index === 0 && "border-t-0")}>
                  <span className="min-w-0 flex-1">
                    {token.label}
                    <div className={t.assessMeta}>
                      {token.token_prefix}… · {token.last_used_at ? `last used ${formatLongDateTime(token.last_used_at)}` : "never used"}
                    </div>
                  </span>
                  {token.revoked_at ? (
                    <Chip>Revoked</Chip>
                  ) : (
                    <button type="button" className={boardButtonSmall} disabled={busy} onClick={() => void act(() => revokeScimToken(orgSlug, token.id))}>
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          )
        }
      </AsyncBoundary>
    </SettingsCard>
  );
}
