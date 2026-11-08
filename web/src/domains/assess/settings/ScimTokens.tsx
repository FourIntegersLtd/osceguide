"use client";

import { LuBan } from "react-icons/lu";
import { RowAction, RowActions } from "@/foundation/ui";
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
    <SettingsCard title="Automatic user sync" lead="For IT teams. Lets your organisation's sign-in system add and remove staff here automatically. Create one key for each system you connect.">
      {failure ? <Note tone="bad" role="alert">{failure}</Note> : null}
      {issued ? (
        <Note tone="warn">
          Copy this key now; it cannot be shown again. <code className="break-all">{issued.token}</code>{" "}
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
          aria-label="Name of the system"
          className={cn(boardInput, "min-w-0 flex-[1_1_240px]")}
          placeholder="Name of the system"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
        />
        <button type="submit" className={boardBtn("primary")} disabled={busy || !label.trim()}>
          Create key
        </button>
      </form>
      <AsyncBoundary state={tokens}>
        {(items) =>
          items.length === 0 ? (
            <p className={cn(t.assessMeta, "m-0")}>No keys yet.</p>
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
                    <Chip>Turned off</Chip>
                  ) : (
                    <RowActions>
                      <RowAction label="Revoke" disabled={busy} onClick={() => void act(() => revokeScimToken(orgSlug, token.id))}>
                        <LuBan className="h-4 w-4" aria-hidden />
                      </RowAction>
                    </RowActions>
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
