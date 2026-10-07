"use client";

import { useState } from "react";
import { Alert, Button } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { hasCode, saveBlob } from "@/foundation/platform-client";
import { can, useSession } from "@/foundation/session";
import { readSittingReadout } from "@/domains/assess/results/api";
import { readoutAsMarkdown, readoutFilename } from "@/domains/assess/results/support";

/**
 * The examination's read-out, as a file the reviewer can hand over.
 *
 * The retiring screen had the same button in the cohort report's header and
 * asked its server for a rendered markdown document. There is no server
 * renderer here — the platform serves the read-out as the JSON document it
 * actually is, with the ranking, the recommendations and the methodology in it
 * — so the markdown is rendered in the browser from that document, by the same
 * formatters the cohort table on screen uses. Nothing is uploaded and nothing is
 * kept: this fetches, hands the bytes to a download, and lets the object URL go.
 *
 * A click, not a load: it is not put through `useAsync` because there is no
 * state to render until somebody asks for the file.
 */
export function ReadoutExport({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const { session } = useSession();
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function exportReadout() {
    setBusy(true);
    setFailure(null);
    setNote(null);
    try {
      const readout = await readSittingReadout(orgSlug, sittingId);
      const markdown = readoutAsMarkdown(readout);
      saveBlob(new Blob([markdown], { type: "text/markdown;charset=utf-8" }), readoutFilename(readout));
    } catch (cause) {
      // Not an examination is not a failure to export — there is simply nothing
      // to export, which is what the cohort screen already says about the same
      // refusal.
      if (hasCode(cause, "not_an_exam_sitting")) {
        setNote("This sitting has no read-out to export.");
      } else {
        setFailure(errorMessage(cause));
      }
    } finally {
      setBusy(false);
    }
  }

  // The readout route is org admin: a supervisor reads the ranking on screen, not as a file.
  if (!can(session, "export_results")) return null;

  return (
    <div className="flex flex-col items-end gap-2">
      <Button
        themeType="b2b"
        variant="ghost"
        size="sm"
        isLoading={busy}
        disabled={busy}
        onClick={() => exportReadout()}
      >
        {busy ? "Exporting…" : "Export readout"}
      </Button>
      {note ? (
        <Alert tone="warning" className="max-w-xs">
          {note}
        </Alert>
      ) : null}
      {failure ? (
        <Alert tone="danger" className="max-w-xs">
          {failure}
        </Alert>
      ) : null}
    </div>
  );
}

