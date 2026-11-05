import { formatMoney, parseApiDate } from "@/foundation/format";
import type { BadgeTone } from "@/foundation/ui";

/** The longest purchase order number the api accepts (`SetPoNumber.po_number`). */
export const PO_NUMBER_MAX = 64;

/**
 * How an invoice's status reads, and whether its PO number may still change.
 *
 * Only an issued invoice takes a PO number; paid and void are final (the api refuses the
 * rest with `invoice_not_editable`). A status this screen does not know is shown as sent and
 * left read only, so a new status never offers a write the api would refuse.
 */
export function describeInvoiceStatus(status: string): { label: string; tone: BadgeTone; poEditable: boolean } {
  if (status === "issued") return { label: "Issued", tone: "info", poEditable: true };
  if (status === "paid") return { label: "Paid", tone: "success", poEditable: false };
  if (status === "void") return { label: "Void", tone: "neutral", poEditable: false };
  return { label: status, tone: "neutral", poEditable: false };
}

/** "£4,800.00" from the invoice's pence, in the invoice's own currency. */
export const invoiceMoney = (pence: number, currency: string): string => formatMoney(pence, currency);

/** "1 Nov 2026", in UK time, as invoices are issued. "-" when there is no date. */
export function invoiceDate(iso: string | null | undefined): string {
  const date = parseApiDate(iso);
  if (!date) return "-";
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/London" });
}

export const poNumberText = (po: string | null): string => po ?? "Not set";

/** The PO number to send, trimmed, or why it cannot be sent. */
export function checkPoNumber(input: string): { ok: true; value: string } | { ok: false; reason: string } {
  const value = input.trim();
  if (value === "") return { ok: false, reason: "Enter a purchase order number." };
  if (value.length > PO_NUMBER_MAX) {
    return { ok: false, reason: `A purchase order number is at most ${PO_NUMBER_MAX} characters.` };
  }
  return { ok: true, value };
}
