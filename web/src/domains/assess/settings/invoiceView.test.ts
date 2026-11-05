import assert from "node:assert/strict";
import { test } from "node:test";
import {
  checkPoNumber,
  describeInvoiceStatus,
  invoiceDate,
  invoiceMoney,
  poNumberText,
} from "@/domains/assess/settings/invoiceView";

test("an issued invoice is open and its PO number can still be set", () => {
  assert.deepEqual(describeInvoiceStatus("issued"), { label: "Issued", tone: "info", poEditable: true });
});

test("a paid or void invoice is final: its PO number is read only", () => {
  assert.deepEqual(describeInvoiceStatus("paid"), { label: "Paid", tone: "success", poEditable: false });
  assert.deepEqual(describeInvoiceStatus("void"), { label: "Void", tone: "neutral", poEditable: false });
});

test("a status the screen does not know is shown as sent and never editable", () => {
  assert.deepEqual(describeInvoiceStatus("disputed"), { label: "disputed", tone: "neutral", poEditable: false });
});

test("money is written from pence in the invoice's own currency", () => {
  assert.equal(invoiceMoney(480000, "gbp"), "£4,800.00");
  assert.equal(invoiceMoney(120000, "GBP"), "£1,200.00");
});

test("dates read as day, short month, year in UK time", () => {
  assert.equal(invoiceDate("2026-11-01T00:00:00Z"), "1 Nov 2026");
  assert.equal(invoiceDate("2026-12-01T00:00:00Z"), "1 Dec 2026");
  assert.equal(invoiceDate(null), "-");
});

test("a missing PO number reads Not set", () => {
  assert.equal(poNumberText(null), "Not set");
  assert.equal(poNumberText("PO-88231"), "PO-88231");
});

test("a PO number is trimmed, must not be empty and is at most 64 characters", () => {
  assert.deepEqual(checkPoNumber("  PO-88231 "), { ok: true, value: "PO-88231" });
  assert.deepEqual(checkPoNumber("   "), { ok: false, reason: "Enter a purchase order number." });
  assert.deepEqual(checkPoNumber("x".repeat(65)), {
    ok: false,
    reason: "A purchase order number is at most 64 characters.",
  });
  assert.deepEqual(checkPoNumber("x".repeat(64)), { ok: true, value: "x".repeat(64) });
});
