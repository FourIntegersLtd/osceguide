"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray } from "react-icons/hi2";
import { productTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { readReceiptDocument, type Receipt } from "@/capabilities/account/api";

const { b2cFieldLabel, b2cFieldValue } = productTokens;

/**
 * Every payment, and the document for it.
 *
 * The old screen offered one "Download receipt" link, and with one payment
 * that is exactly what this renders. A person with several payments gets a
 * row per payment, because the backend has always kept one per payment and
 * the old single link could reach only one of them.
 */
export default function ReceiptList({ receipts }: { receipts: Receipt[] }) {
  const [single] = receipts;
  if (receipts.length === 1 && single) return <ReceiptLink receipt={single} />;

  return (
    <ul className="divide-y divide-b2c-border rounded-xl border border-b2c-border">
      {receipts.map((receipt) => (
        <ReceiptRow key={receipt.receipt_id} receipt={receipt} />
      ))}
    </ul>
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

const LINK_CLASS =
  "inline-flex shrink-0 items-center gap-2 text-osce-body font-medium text-osce-accent transition hover:text-osce-accent-hover disabled:cursor-not-allowed disabled:opacity-60";

/** The old screen's single link, word for word. */
function ReceiptLink({ receipt }: { receipt: Receipt }) {
  const { isOpening, error, openDocument } = useReceiptDocument(receipt);
  return (
    <div>
      <button type="button" onClick={() => void openDocument()} disabled={isOpening} className={LINK_CLASS}>
        <HiOutlineArrowDownTray className="h-4 w-4 shrink-0" aria-hidden />
        {isOpening ? "Downloading…" : "Download receipt"}
      </button>
      {error ? <p className="mt-1 text-osce-meta text-osce-danger">{error}</p> : null}
    </div>
  );
}

function ReceiptRow({ receipt }: { receipt: Receipt }) {
  const { isOpening, error, openDocument } = useReceiptDocument(receipt);

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <p className={b2cFieldValue}>{receipt.plan_label}</p>
        {/*
          Printed exactly as the backend wrote them. `paid_at` and
          `amount_total` are already display strings — "16 September 2026",
          "£99.00" — pinned by a receipt oracle against the legacy formatter,
          not ISO timestamps and pence. Re-formatting them here would make the
          screen and the printed document disagree about a financial figure,
          and `new Date("16 September 2026")` renders a dash on most browsers.
        */}
        <p className={b2cFieldLabel}>
          {receipt.paid_at} · {receipt.amount_total}
        </p>
        {error ? <p className="mt-1 text-osce-meta text-osce-danger">{error}</p> : null}
      </div>
      <button type="button" onClick={() => void openDocument()} disabled={isOpening} className={LINK_CLASS}>
        <HiOutlineArrowDownTray className="h-4 w-4 shrink-0" aria-hidden />
        {isOpening ? "Downloading…" : "Download receipt"}
      </button>
    </li>
  );
}
