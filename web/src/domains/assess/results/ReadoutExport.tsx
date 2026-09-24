"use client";

import { useState } from "react";
import { Alert, Button } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
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
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function exportReadout() {
    setBusy(true);
    setFailure(null);
    setNote(null);
    try {
      const readout = await readSittingReadout(orgSlug, sittingId);
      downloadText(readoutFilename(readout), readoutAsMarkdown(readout));
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

  return (
    <div className="flex flex-col items-end gap-2">
      <Button
        themeType="b2b"
        variant="secondary"
        size="sm"
        isLoading={busy}
        disabled={busy}
        onClick={() => void exportReadout()}
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

function downloadText(filename: string, text: string): void {
  const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = filename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  // The download reads the blob when the click is handled, so the URL can go as
  // soon as this turn is finished — and if it never does, the blob is one file's
  // worth of JSON.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
