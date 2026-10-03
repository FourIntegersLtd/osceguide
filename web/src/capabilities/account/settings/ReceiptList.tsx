"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray, HiOutlineDocumentText } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { readReceiptDocument, type Receipt } from "@/capabilities/account/api";
import { SettingsRow, SettingsRows } from "@/capabilities/account/settings/SettingsKit";

/**
 * Every payment, and the document for it.
 *
 * A row per payment, because the backend has always kept one per payment and
 * the old screen's single "Download receipt" link could reach only one.
 */
export default function ReceiptList({ receipts }: { receipts: Receipt[] }) {
  return (
    <SettingsRows>
      {receipts.map((receipt) => (
        <ReceiptRow key={receipt.receipt_id} receipt={receipt} />
      ))}
    </SettingsRows>
  );
}

/**
 * Opened, not saved. The route serves the document inline precisely so that
 * a browser can show it and print it to PDF; forcing a download would stop
 * somebody simply looking at what they were charged. It cannot be a plain
 * link either — the route wants a bearer token — so the markup is fetched
 * and handed to a tab as a blob.
 */
function useReceiptDocument(receipt: Receipt) {
  const [isOpening, setIsOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openDocument = async () => {
    setError(null);
    setIsOpening(true);
    try {
      const html = await readReceiptDocument(receipt.receipt_id);
      const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
      const opened = window.open(url, "_blank", "noopener,noreferrer");
      if (!opened) setError("Your browser blocked the receipt window. Allow pop-ups and try again.");
      // Long enough for the new tab to have loaded it; the object is the tab's
      // after that, and keeping the handle leaks the document into this page.
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setIsOpening(false);
    }
  };

  return { isOpening, error, openDocument };
}

function ReceiptRow({ receipt }: { receipt: Receipt }) {
  const { isOpening, error, openDocument } = useReceiptDocument(receipt);

  /*
    Printed exactly as the backend wrote them. `paid_at` and `amount_total`
    are already display strings — "16 September 2026", "£99.00" — pinned by a
    receipt oracle against the legacy formatter, not ISO timestamps and pence.
    Re-formatting them here would make the screen and the printed document
    disagree about a financial figure, and `new Date("16 September 2026")`
    renders a dash on most browsers.
  */
  return (
    <SettingsRow
      icon={HiOutlineDocumentText}
      title={`${receipt.plan_label} · ${receipt.amount_total}`}
      meta={`Paid ${receipt.paid_at}`}
      trailing={
        <Button variant="ghost" size="sm" onClick={() => void openDocument()} disabled={isOpening} className="gap-2">
          <HiOutlineArrowDownTray className="h-4 w-4 shrink-0" aria-hidden />
          {isOpening ? "Downloading…" : "Download receipt"}
        </Button>
      }
    >
      {error ? <p className="mt-1 text-osce-meta text-danger">{error}</p> : null}
    </SettingsRow>
  );
}
