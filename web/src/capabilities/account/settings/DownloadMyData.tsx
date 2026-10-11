"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray } from "react-icons/hi2";
import { Button, Panel } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { exportMyData, exportMyDataPdf } from "@/capabilities/account/api";
import { settingsSub } from "@/capabilities/account/settings/SettingsKit";

/**
 * The self-serve subject access request (E-5): everything this account owns,
 * as one JSON file the browser saves rather than displays.
 *
 * `GET /me/export` answers the object directly — `platformRequest` reads
 * JSON regardless of the backend's `Content-Disposition` header, since that
 * header only steers a browser navigating there directly — so this builds
 * the file itself and hands it to `saveBlob`.
 */
export function DownloadMyData() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (save: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await save();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const formats = [
    {
      label: busy ? "Preparing…" : "Download my data",
      save: async () => {
        const data = await exportMyData();
        saveBlob(
          new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
          "my-data.json",
        );
      },
    },
    {
      label: "Download as PDF",
      save: async () => saveBlob(await exportMyDataPdf(), "my-data.pdf"),
    },
  ];

  return (
    <Panel title="Your data">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className={settingsSub}>A copy of everything we hold about you.</p>
          {error ? <p className="mt-1 text-osce-meta text-danger">{error}</p> : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          {formats.map(({ label, save }) => (
            <Button
              key={label}
              variant="secondary"
              onClick={() => run(save)}
              disabled={busy}
              className="gap-2"
            >
              <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
              {label}
            </Button>
          ))}
        </div>
      </div>
    </Panel>
  );
}
