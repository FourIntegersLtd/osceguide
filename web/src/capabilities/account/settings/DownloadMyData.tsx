"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray, HiOutlineDocumentText } from "react-icons/hi2";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalHelper,
  ModalSecondaryButton,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { exportMyData } from "@/capabilities/account/api";

const { b2cSettingsCardHeaderIcon } = productTokens;

/**
 * The self-serve subject access request (E-5): everything this account owns,
 * as one JSON file the browser saves rather than displays.
 *
 * `GET /me/export` answers the object directly — `platformRequest` reads
 * JSON regardless of the backend's `Content-Disposition` header, since that
 * header only steers a browser navigating there directly — so this builds
 * the download itself from a `Blob`, the same way `ReceiptList` turns a
 * fetched receipt document into an opened tab.
 */
export function DownloadMyData() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await exportMyData();
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "my-data.json";
      // Never attached to the page, so nothing is left behind if the click
      // handler throws before the browser reads it.
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>
        <HiOutlineDocumentText className={b2cSettingsCardHeaderIcon} aria-hidden />
        Your data
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-3">
        <ModalHelper className="mt-0">
          Download everything this account owns: your profile, your attempts with their
          transcripts and marks, and your payments — one file, ready to keep or hand to
          anyone who asks what we hold about you.
        </ModalHelper>
        {error ? <p className="text-osce-meta text-osce-danger">{error}</p> : null}
      </B2CPanelCardBody>
      <B2CPanelCardFooter>
        <ModalSecondaryButton type="button" onClick={() => void download()} disabled={busy} className="gap-2">
          <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
          {busy ? "Preparing…" : "Download my data"}
        </ModalSecondaryButton>
      </B2CPanelCardFooter>
    </B2CPanelCard>
  );
}
