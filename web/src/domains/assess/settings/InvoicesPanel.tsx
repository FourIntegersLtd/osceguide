"use client";

import { useState } from "react";
import { AsyncBoundary, b2bTokens as t, cn, LeaveConfirmModal } from "@/foundation/ui";
import { cardTitle } from "@/domains/assess/settings/SettingsCard";
import { card, Chip, hint, Note, row, th } from "@/domains/assess/ui";
import { errorMessage, useAsync, useCursorPages, useDirtyGuard } from "@/foundation/hooks";
import { formatMoney, formatShortDate } from "@/foundation/format";
import { PlatformError } from "@/foundation/platform-client";
import {
  listInvoices,
  readInvoice,
  setInvoicePoNumber,
  type Invoice,
} from "@/domains/assess/api";
import {
  checkPoNumber,
  describeInvoiceStatus,
  PO_NUMBER_MAX,
} from "@/domains/assess/settings/invoiceView";
import { boardBtn, boardPadWide, boardInput, boardLabel, type BoardChipTone, boardButtonSmall } from "@/foundation/ui/boardKit";

/**
 * The invoices OSCE Guide has raised for this organisation (org admin only), on `/settings/invoices`.
 *
 * Read only except for one field: the organisation's own purchase order number, which the api
 * accepts until the invoice is paid or void. Raising, paying and voiding stay in the staff console.
 */
export function InvoiceBrowser({ orgSlug, setDirty }: { orgSlug: string; setDirty: (dirty: boolean) => void }) {
  const [openId, setOpenId] = useState<string | null>(null);
  return openId ? (
    <InvoiceDetail key={openId} orgSlug={orgSlug} invoiceId={openId} setDirty={setDirty} onBack={() => setOpenId(null)} />
  ) : (
    <InvoiceList orgSlug={orgSlug} onOpen={setOpenId} />
  );
}

/** The invoice status as the board's chip. */
function StatusChip({ status }: { status: string }) {
  const described = describeInvoiceStatus(status);
  const tone: BoardChipTone = described.tone === "success" ? "ok" : described.tone === "info" ? "info" : "neutral";
  return <Chip tone={tone}>{described.label}</Chip>;
}

function InvoiceList({ orgSlug, onOpen }: { orgSlug: string; onOpen: (id: string) => void }) {
  const pages = useCursorPages((cursor, signal) => listInvoices(orgSlug, signal, { cursor }), [orgSlug]);

  return (
    <AsyncBoundary state={pages.state}>
      {(items) => {
        if (items.length === 0) {
          return (
            <div className={cn(boardPadWide)}>
              <h2 className={cardTitle}>No invoices yet.</h2>
              <p className={cn(t.assessMeta, "m-0")}>Invoices OSCE Guide raises for your organisation appear here.</p>
            </div>
          );
        }
        return (
          <div className={card}>
            {pages.moreError ? <Note tone="bad">{errorMessage(pages.moreError)}</Note> : null}
            <div className={th}>
              <span className="min-w-40 flex-[1_1_160px]">Invoice</span>
              <span className="w-[110px]">Issued</span>
              <span className="w-[110px]">Due</span>
              <span className="w-[100px]">Total</span>
              <span className="w-20">Status</span>
              <span className="w-[110px]">PO number</span>
              <span className="w-[60px]" />
            </div>
            {items.map((invoice) => (
              <div key={invoice.id} className={row}>
                <span className="min-w-40 flex-[1_1_160px] font-medium">{invoice.invoice_number}</span>
                <span className={cn("w-[110px]", t.assessMeta)}>{formatShortDate(invoice.issued_at)}</span>
                <span className={cn("w-[110px]", t.assessMeta)}>{formatShortDate(invoice.due_at)}</span>
                <span className="w-[100px]">{formatMoney(invoice.total_pence, invoice.currency)}</span>
                <span className="w-20">
                  <StatusChip status={invoice.status} />
                </span>
                <span className={cn("w-[110px]", t.assessMeta)}>{invoice.po_number ?? "Not set"}</span>
                <button type="button" className={boardButtonSmall} aria-label={`Open ${invoice.invoice_number}`} onClick={() => onOpen(invoice.id)}>
                  Open
                </button>
              </div>
            ))}
            {pages.hasMore ? (
              <div className={cn(row, "justify-center")}>
                <button type="button" className={boardButtonSmall} disabled={pages.loadingMore} onClick={pages.loadMore}>
                  {pages.loadingMore ? "Loading…" : "Load more"}
                </button>
              </div>
            ) : null}
          </div>
        );
      }}
    </AsyncBoundary>
  );
}

function InvoiceDetail({
  orgSlug,
  invoiceId,
  setDirty,
  onBack,
}: {
  orgSlug: string;
  invoiceId: string;
  setDirty: (dirty: boolean) => void;
  onBack: () => void;
}) {
  const state = useAsync((signal) => readInvoice(orgSlug, invoiceId, signal), [orgSlug, invoiceId]);
  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(invoice) => (
          <InvoiceBody
            key={invoice.po_number ?? ""}
            orgSlug={orgSlug}
            invoice={invoice}
            onChanged={state.reload}
            setDirty={setDirty}
            onBack={onBack}
          />
        )}
      </AsyncBoundary>
      {state.data ? null : (
        <div>
          <button type="button" className={boardBtn("ghost", true)} onClick={onBack}>
            Back to invoices
          </button>
        </div>
      )}
    </div>
  );
}

function InvoiceBody({
  orgSlug,
  invoice,
  onChanged,
  setDirty,
  onBack,
}: {
  orgSlug: string;
  invoice: Invoice;
  onChanged: () => void;
  setDirty: (dirty: boolean) => void;
  onBack: () => void;
}) {
  const status = describeInvoiceStatus(invoice.status);
  const [po, setPo] = useState(invoice.po_number ?? "");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const checked = checkPoNumber(po);
  const unchanged = checked.ok && checked.value === invoice.po_number;
  const edited = po !== (invoice.po_number ?? "");
  const [leaving, setLeaving] = useState(false);
  // The tab strip's "Leave without saving?" guard follows an edited, unsaved PO number.
  useDirtyGuard(edited, setDirty);

  async function save() {
    if (!checked.ok) return;
    setBusy(true);
    setFailure(null);
    try {
      await setInvoicePoNumber(orgSlug, invoice.id, checked.value);
      onChanged();
    } catch (cause) {
      if (cause instanceof PlatformError && cause.code === "invoice_not_editable") {
        setFailure("That invoice is paid or cancelled, so its purchase order number can no longer change.");
        onChanged();
      } else {
        setFailure(errorMessage(cause));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={boardPadWide}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className={cardTitle}>{invoice.invoice_number}</h2>
          <div className={t.assessMeta}>
            {invoice.customer_name} · issued {formatShortDate(invoice.issued_at)} · due {formatShortDate(invoice.due_at)}
          </div>
        </div>
        <StatusChip status={invoice.status} />
      </div>
      <div className={card}>
        <div className={th}>
          <span className="flex-1">Line</span>
          <span className="w-[60px]">Qty</span>
          <span className="w-[100px]">Amount</span>
        </div>
        {invoice.lines.map((line) => (
          <div key={line.position} className={row}>
            <span className="flex-1">{line.description}</span>
            <span className="w-[60px]">{line.quantity}</span>
            <span className="w-[100px]">{formatMoney(line.amount_pence, invoice.currency)}</span>
          </div>
        ))}
        <div className={row}>
          <b className="flex-1">Total</b>
          <span className="w-[60px]" />
          <b className="w-[100px]">{formatMoney(invoice.total_pence, invoice.currency)}</b>
        </div>
      </div>
      {failure ? <Note tone="bad" role="alert">{failure}</Note> : null}
      {status.poEditable ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <label htmlFor="invoice-po" className={boardLabel}>
            Purchase order number
          </label>
          <div className="flex gap-2">
            <input
              id="invoice-po"
              className={cn(boardInput, "max-w-[260px]")}
              value={po}
              maxLength={PO_NUMBER_MAX}
              onChange={(event) => setPo(event.target.value)}
            />
            <button type="submit" className={boardBtn("primary")} disabled={busy || !checked.ok || unchanged}>
              {busy ? "Saving…" : "Save PO number"}
            </button>
          </div>
          {edited && !checked.ok ? (
            <p role="alert" className="mt-1.5 text-assess-meta text-osce-danger-text">
              {checked.reason} To remove one, contact support.
            </p>
          ) : null}
          <div className={hint}>Your finance team&apos;s reference. It can change until the invoice is paid or cancelled.</div>
        </form>
      ) : (
        <p className={cn(t.assessMeta, "m-0")}>Purchase order number: {invoice.po_number ?? "Not set"}</p>
      )}
      {invoice.notes ? <div className={t.assessMeta}>Notes from OSCE Guide: {invoice.notes}</div> : null}
      <button type="button" className={cn(boardBtn("ghost", true), "self-start")} onClick={() => (edited ? setLeaving(true) : onBack())}>
        Back to invoices
      </button>
      <LeaveConfirmModal isOpen={leaving} onStay={() => setLeaving(false)} onLeave={onBack} />
    </section>
  );
}
