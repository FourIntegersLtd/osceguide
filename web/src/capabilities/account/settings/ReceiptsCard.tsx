"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray, HiOutlineReceiptPercent } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,

  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { listReceipts, readReceiptDocument, type Receipt } from "@/capabilities/account/api";
import { SUPPORT_EMAIL } from "@/capabilities/account/settings/PlanPicker";

const { b2cFieldLabel, b2cFieldValue, b2cLink, b2cSettingsCardHeaderIcon } = productTokens;

/**
 * Every payment, and the document for it.
 *
 * The old screen asked one endpoint whether "a receipt" was available and
 * offered a single download; a person with three payments could reach one of
 * them. There is a row per payment here because the backend has always kept
 * one per payment.
 */
export default function ReceiptsCard() {
  const receipts = useAsync((signal) => listReceipts(signal), []);

  return (
    <B2CPanelCard className="mt-0 overflow-hidden">
      <B2CPanelCardHeader>
        <HiOutlineReceiptPercent className={b2cSettingsCardHeaderIcon} aria-hidden />
        Receipts
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <AsyncBoundary
          state={receipts}
          empty={{
            title: "No receipts yet",
            description: (
              <>
                Anything you buy shows up here.{" "}
                <a href={`mailto:${SUPPORT_EMAIL}`} className={b2cLink}>
                  Contact support
                </a>{" "}
                if you need confirmation of a payment.
              </>
            ),
          }}
        >
          {(items: Receipt[]) => (
            <ul className="divide-y divide-b2c-border rounded-xl border border-b2c-border">
              {items.map((receipt) => (
                <ReceiptRow key={receipt.receipt_id} receipt={receipt} />
              ))}
            </ul>
          )}
        </AsyncBoundary>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function ReceiptRow({ receipt }: { receipt: Receipt }) {
  const [isOpening, setIsOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /*
   * Opened, not saved. The route serves the document inline precisely so that
   * a browser can show it and print it to PDF; forcing a download would stop
   * somebody simply looking at what they were charged. It cannot be a plain
   * link either — the route wants a bearer token — so the markup is fetched
   * and handed to a tab as a blob.
   */
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
      <button
        type="button"
        onClick={() => void openDocument()}
        disabled={isOpening}
        className="inline-flex shrink-0 items-center gap-2 text-osce-body font-medium text-osce-accent transition hover:text-osce-accent-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        <HiOutlineArrowDownTray className="h-4 w-4 shrink-0" aria-hidden />
        {isOpening ? "Opening…" : "View receipt"}
      </button>
    </li>
  );
}

