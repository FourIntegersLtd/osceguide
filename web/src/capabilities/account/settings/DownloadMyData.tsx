"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray } from "react-icons/hi2";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { exportMyDataPdf } from "@/capabilities/account/api";
import { AccountButton, AccountCard, useBoardSkin } from "@/capabilities/account/settings/AccountKit";
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

  const board = useBoardSkin();

  return (
    <AccountCard title="Your data" description={board ? "A copy of everything we hold about you." : undefined}>
      <div className={board ? "flex flex-col items-start gap-4" : "flex flex-wrap items-center justify-between gap-3"}>
        {board ? null : (
          <div className="min-w-0 flex-1">
            <p className={settingsSub}>A copy of everything we hold about you.</p>
            {error ? <p className="mt-1 text-osce-meta text-danger">{error}</p> : null}
          </div>
        )}
        {board && error ? <p className="m-0 text-assess-meta text-osce-danger-text">{error}</p> : null}
        <AccountButton variant="secondary" icon={HiOutlineArrowDownTray} onClick={download} disabled={busy} className="shrink-0">
          Download as PDF
        </AccountButton>
      </div>
    </AccountCard>
  );
}
