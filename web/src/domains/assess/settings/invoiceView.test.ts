import assert from "node:assert/strict";
import { test } from "node:test";
import { checkPoNumber, describeInvoiceStatus } from "@/domains/assess/settings/invoiceView";

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

test("a PO number is trimmed, must not be empty and is at most 64 characters", () => {
  assert.deepEqual(checkPoNumber("  PO-88231 "), { ok: true, value: "PO-88231" });
  assert.deepEqual(checkPoNumber("   "), { ok: false, reason: "Enter a purchase order number." });
  assert.deepEqual(checkPoNumber("x".repeat(65)), {
    ok: false,
    reason: "A purchase order number is at most 64 characters.",
  });
  assert.deepEqual(checkPoNumber("x".repeat(64)), { ok: true, value: "x".repeat(64) });
});
