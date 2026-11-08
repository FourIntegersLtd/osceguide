import assert from "node:assert/strict";
import test from "node:test";
import type { Scheme } from "@/domains/assess/room/api";
import { domainsOf, firstOpen, nextOpen } from "@/domains/assess/room/schemeDomains";

const scheme = (outline: unknown[]) => ({ slot_id: "s", structure: { outline } }) as unknown as Scheme;

const flat = domainsOf(scheme([{ block: "domain", id: "a", title: "Opening" }, { block: "domain", id: "b", title: "Closing" }]));
const nested = domainsOf(
  scheme([
    { block: "domain", id: "a", title: "Opening", competencies: [{ id: "c1", label: "Greets" }, { id: "c2", label: "Names role" }] },
    { block: "notes", id: "n", title: "Faculty" },
  ]),
);

test("a domain with no competencies is one item keyed by the domain", () => {
  assert.deepEqual(flat.map((d) => d.items), [[{ key: "a", label: "Opening" }], [{ key: "b", label: "Closing" }]]);
});

test("competencies become items keyed domain.competency, and non-domain blocks are skipped", () => {
  assert.deepEqual(nested.map((d) => d.id), ["a"]);
  assert.deepEqual(nested[0]?.items, [
    { key: "a.c1", label: "Greets" },
    { key: "a.c2", label: "Names role" },
  ]);
});

test("firstOpen is the first domain with something unmarked, else the first", () => {
  assert.equal(firstOpen(flat, (key) => key === "a"), "b");
  assert.equal(firstOpen(flat, () => true), "a");
  assert.equal(firstOpen([], () => false), null);
});

test("nextOpen wraps round to an earlier domain and is null when everything is marked", () => {
  assert.equal(nextOpen(flat, "b", (key) => key === "b"), "a");
  assert.equal(nextOpen(flat, "a", (key) => key === "a"), "b");
  assert.equal(nextOpen(flat, "a", () => true), null);
});
