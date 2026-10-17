"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray } from "react-icons/hi2";
import { Button, Panel } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { exportMyDataPdf } from "@/capabilities/account/api";
import { settingsSub } from "@/capabilities/account/settings/SettingsKit";

/**
 * The self-serve subject access request (E-5): everything this account owns, as
 * one PDF a person can read and print. `GET /me/export` answers the file, which
 * `saveBlob` hands to the browser to save rather than display.
 */
export function DownloadMyData() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async () => {
    setBusy(true);
    setError(null);
    try {
      saveBlob(await exportMyDataPdf(), "my-data.pdf");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="Your data">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className={settingsSub}>A copy of everything we hold about you.</p>
          {error ? <p className="mt-1 text-osce-meta text-danger">{error}</p> : null}
        </div>
        <Button variant="secondary" onClick={download} disabled={busy} className="shrink-0 gap-2">
          <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
          Download as PDF
        </Button>
      </div>
    </Panel>
  );
}
