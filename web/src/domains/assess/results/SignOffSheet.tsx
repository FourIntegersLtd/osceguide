"use client";

import { useCallback, useState } from "react";
import { b2bTokens as t } from "@/foundation/ui";
import { boardAlert, boardBtn } from "@/foundation/ui/boardKit";
import { useAssessWords } from "@/capabilities/assess-words";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { signOffDecisions } from "@/domains/assess/results/api";
import { SIGN_OFF_SHEET_LABEL, signedOffByLine } from "@/domains/assess/results/hireDecisions";

/**
 * Signing off the whole sheet on the hire decisions page: waits until every candidate has a decision
 * (`gate` says how many are left), then one request signs them all or none. Once signed it names who and when.
 */
export function SignOffSheet({
  orgSlug,
  sittingId,
  gate,
  signature,
  canSign,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  gate: string | null;
  signature: { name: string | null; at: string } | null;
  canSign: boolean;
  onChanged: () => void;
}) {
  const w = useAssessWords();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const signOff = useCallback(async () => {
    setBusy(true);
    setFailure(null);
    try {
      await signOffDecisions(orgSlug, sittingId);
      onChanged();
    } catch (cause) {
      setFailure(assessErrorMessage(cause, w));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, sittingId, onChanged, w]);

  return (
    <div className="flex flex-col gap-2">
      {signature ? (
        <div role="status" className={t.assessMeta}>{signedOffByLine(signature, new Date())}</div>
      ) : canSign ? (
        <>
          <div className="flex flex-wrap items-center gap-2.5">
            <button type="button" className={boardBtn("primary")} disabled={busy || gate !== null} onClick={() => void signOff()}>
              {SIGN_OFF_SHEET_LABEL}
            </button>
            {gate ? <span className="text-assess-label text-osce-ink-700">{gate}</span> : null}
          </div>
        </>
      ) : null}
      {failure ? <div role="alert" className={boardAlert("bad")}>{failure}</div> : null}
    </div>
  );
}
