"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray } from "react-icons/hi2";
import {
  ModalHelper,
  ModalSecondaryButton,
  Panel,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { exportMyData } from "@/capabilities/account/api";

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

  const download = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await exportMyData();
      saveBlob(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
        "my-data.json",
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="Your data">
      <div className="space-y-3">
        <ModalHelper className="mt-0">
          Download everything this account owns: your profile, your attempts with their
          transcripts and marks, and your payments — one file, ready to keep or hand to
          anyone who asks what we hold about you.
        </ModalHelper>
        {error ? <p className="text-osce-meta text-osce-danger">{error}</p> : null}
      </div>
      <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
        <ModalSecondaryButton type="button" onClick={() => void download()} disabled={busy} className="gap-2">
          <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
          {busy ? "Preparing…" : "Download my data"}
        </ModalSecondaryButton>
      </div>
    </Panel>
  );
}
