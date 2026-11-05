"use client";

import { useEffect, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, EmptyState, Input, LeaveConfirmModal, Panel } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { PlatformError } from "@/foundation/platform-client";
import {
  listInvoices,
  readInvoice,
  readOrganization,
  setInvoicePoNumber,
  type Invoice,
} from "@/domains/assess/api";
import {
  checkPoNumber,
  describeInvoiceStatus,
  invoiceDate,
  invoiceMoney,
  PO_NUMBER_MAX,
  poNumberText,
} from "@/domains/assess/settings/invoiceView";

/**
 * The invoices OSCE Guide has raised for this organisation (org admin only).
 *
 * Read only except for one field: the organisation's own purchase order number, which the api
 * accepts until the invoice is paid or void. Raising, paying and voiding stay in the staff console.
 */
export function InvoicesPanel({ orgSlug, setDirty }: { orgSlug: string; setDirty: (dirty: boolean) => void }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const org = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  const description = `Invoices OSCE Guide raises for ${org.data?.name ?? "your organisation"}, and the purchase order number your finance team needs on them.`;
  return (
    <Panel title="Invoices" description={description}>
      {openId ? (
        <InvoiceDetail key={openId} orgSlug={orgSlug} invoiceId={openId} setDirty={setDirty} onBack={() => setOpenId(null)} />
      ) : (
        <InvoiceList orgSlug={orgSlug} onOpen={setOpenId} />
      )}
    </Panel>
  );
}

function InvoiceList({ orgSlug, onOpen }: { orgSlug: string; onOpen: (id: string) => void }) {
  const first = useAsync((signal) => listInvoices(orgSlug, signal), [orgSlug]);
  const [more, setMore] = useState<Invoice[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const next = cursor === undefined ? first.data?.next_cursor : cursor;

  async function loadMore() {
    if (!next) return;
    setBusy(true);
    setFailure(null);
    try {
      const page = await listInvoices(orgSlug, undefined, { cursor: next });
      setMore((current) => [...current, ...page.items]);
      setCursor(page.next_cursor ?? null);
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AsyncBoundary state={first}>
      {(page) => {
        const items = [...page.items, ...more];
        if (items.length === 0) {
          return (
            <EmptyState
              bare
              title="No invoices yet."
              description="Invoices OSCE Guide raises for your organisation appear here."
            />
          );
        }
        return (
          <div className="flex flex-col gap-3">
            {failure ? <Alert tone="danger">{failure}</Alert> : null}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-osce-body">
                <thead className="text-osce-caption uppercase text-ink-muted">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Invoice</th>
                    <th className="py-2 pr-4 font-medium">Issued</th>
                    <th className="py-2 pr-4 font-medium">Due</th>
                    <th className="py-2 pr-4 font-medium">Total</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium">PO number</th>
                    <th className="py-2 font-medium">
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((invoice) => {
                    const status = describeInvoiceStatus(invoice.status);
                    return (
                      <tr key={invoice.id} className="border-t border-border">
                        <td className="py-3 pr-4 font-medium text-ink">{invoice.invoice_number}</td>
                        <td className="py-3 pr-4 text-ink-muted">{invoiceDate(invoice.issued_at)}</td>
                        <td className="py-3 pr-4 text-ink-muted">{invoiceDate(invoice.due_at)}</td>
                        <td className="py-3 pr-4">{invoiceMoney(invoice.total_pence, invoice.currency)}</td>
                        <td className="py-3 pr-4">
                          <Badge variant={status.tone}>{status.label}</Badge>
                        </td>
                        <td className="py-3 pr-4 text-ink-muted">{poNumberText(invoice.po_number)}</td>
                        <td className="py-3">
                          <Button
                            variant="secondary"
                            size="sm"
                            aria-label={`Open ${invoice.invoice_number}`}
                            onClick={() => onOpen(invoice.id)}
                          >
                            Open
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {next ? (
              <div className="flex justify-center">
                <Button variant="secondary" size="sm" disabled={busy} onClick={() => void loadMore()}>
                  {busy ? "Loading…" : "Load more"}
                </Button>
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
  const [dirty, setLocalDirty] = useState(false);
  const [leaving, setLeaving] = useState(false);
  // The tab strip's "Leave without saving?" guard follows an edited, unsaved PO number.
  useEffect(() => {
    setDirty(dirty);
    return () => setDirty(false);
  }, [dirty, setDirty]);
  return (
    <div className="flex flex-col gap-4">
      <AsyncBoundary state={state}>
        {(invoice) => <InvoiceBody key={invoice.po_number ?? ""} orgSlug={orgSlug} invoice={invoice} onChanged={state.reload} onDirty={setLocalDirty} />}
      </AsyncBoundary>
      <div>
        <Button variant="ghost" size="sm" onClick={() => (dirty ? setLeaving(true) : onBack())}>
          Back to invoices
        </Button>
      </div>
      <LeaveConfirmModal isOpen={leaving} onStay={() => setLeaving(false)} onLeave={onBack} />
    </div>
  );
}

function InvoiceBody({
  orgSlug,
  invoice,
  onChanged,
  onDirty,
}: {
  orgSlug: string;
  invoice: Invoice;
  onChanged: () => void;
  onDirty: (dirty: boolean) => void;
}) {
  const status = describeInvoiceStatus(invoice.status);
  const [po, setPo] = useState(invoice.po_number ?? "");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const checked = checkPoNumber(po);
  const unchanged = checked.ok && checked.value === invoice.po_number;
  const edited = po !== (invoice.po_number ?? "");
  useEffect(() => {
    onDirty(edited);
  }, [edited, onDirty]);

  async function save() {
    if (!checked.ok) return;
    setBusy(true);
    setFailure(null);
    try {
      await setInvoicePoNumber(orgSlug, invoice.id, checked.value);
      onChanged();
    } catch (cause) {
      if (cause instanceof PlatformError && cause.code === "invoice_not_editable") {
        setFailure("That invoice is paid or void, so its purchase order number can no longer change.");
        onChanged();
      } else {
        setFailure(errorMessage(cause));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-osce-data font-semibold text-ink">{invoice.invoice_number}</h3>
          <p className="text-osce-meta text-ink-muted">
            {invoice.customer_name} · issued {invoiceDate(invoice.issued_at)} · due {invoiceDate(invoice.due_at)}
          </p>
        </div>
        <Badge variant={status.tone}>{status.label}</Badge>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-osce-body">
          <thead className="text-osce-caption uppercase text-ink-muted">
            <tr>
              <th className="py-2 pr-4 font-medium">Line</th>
              <th className="py-2 pr-4 font-medium">Qty</th>
              <th className="py-2 font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.lines.map((line) => (
              <tr key={line.position} className="border-t border-border">
                <td className="py-3 pr-4">{line.description}</td>
                <td className="py-3 pr-4">{line.quantity}</td>
                <td className="py-3">{invoiceMoney(line.amount_pence, invoice.currency)}</td>
              </tr>
            ))}
            <tr className="border-t border-border font-semibold">
              <td className="py-3 pr-4">Total</td>
              <td className="py-3 pr-4" />
              <td className="py-3">{invoiceMoney(invoice.total_pence, invoice.currency)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      {status.poEditable ? (
        <form
          className="flex max-w-xl flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <div className="flex items-end gap-3">
            <Input
              label="Purchase order number"
              value={po}
              maxLength={PO_NUMBER_MAX}
              onChange={(event) => setPo(event.target.value)}
            />
            <Button type="submit" disabled={busy || !checked.ok || unchanged}>
              {busy ? "Saving…" : "Save PO number"}
            </Button>
          </div>
          {edited && !checked.ok ? (
            <p role="alert" className="text-osce-meta text-danger">
              {checked.reason} To remove one, contact support.
            </p>
          ) : null}
          <p className="text-osce-caption text-ink-muted">
            Your finance team&apos;s reference. It can change until the invoice is paid or void.
          </p>
        </form>
      ) : (
        <p className="text-osce-body text-ink-muted">Purchase order number: {poNumberText(invoice.po_number)}</p>
      )}
      {invoice.notes ? <p className="text-osce-meta text-ink-muted">Notes from OSCE Guide: {invoice.notes}</p> : null}
    </div>
  );
}
