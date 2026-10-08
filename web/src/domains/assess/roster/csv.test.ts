import assert from "node:assert/strict";
import test from "node:test";
import { parseTraineeCsv, splitCsvLine } from "@/domains/assess/roster/csv";

test("a quoted field containing a comma stays one field", () => {
  assert.deepEqual(splitCsvLine('"Khan, Amina",amina@nhs.uk'), ["Khan, Amina", "amina@nhs.uk"]);
});

test("a doubled quote inside a quoted field is one quote", () => {
  assert.deepEqual(splitCsvLine('"she said ""hi""",b@c.uk'), ['she said "hi"', "b@c.uk"]);
});

test("headers are matched whatever their case and spacing", () => {
  const parsed = parseTraineeCsv(" Email , First Name , LastName , Group \na@b.uk,Amina,Khan,June 2026");
  assert.equal(parsed.error, null);
  assert.deepEqual(parsed.rows, [
    { email: "a@b.uk", firstName: "Amina", lastName: "Khan", cohort: "June 2026" },
  ]);
});

test("a file with no email column is refused rather than half-imported", () => {
  const parsed = parseTraineeCsv("name,cohort\nAmina,June");
  assert.equal(parsed.rows.length, 0);
  assert.match(parsed.error ?? "", /email/);
});

test("rows with no usable address are reported by line number, not dropped silently", () => {
  const parsed = parseTraineeCsv("email,firstName\na@b.uk,Amina\n,Nobody\nnot-an-address,Someone");
  assert.equal(parsed.rows.length, 1);
  assert.deepEqual(parsed.skippedLines, [3]);
  assert.deepEqual(parsed.invalidLines, [4]);
  assert.equal(parsed.error, null);
});

test("addresses are lowercased, so a re-import matches what is already there", () => {
  const parsed = parseTraineeCsv("email\nAmina@NHS.uk");
  assert.equal(parsed.rows[0]?.email, "amina@nhs.uk");
});

test("a name column is split on the first space into first and last", () => {
  const parsed = parseTraineeCsv("Name,Email\nAmina Khan,a@b.uk\nMary Ann Lee,m@b.uk\nPrince,p@b.uk");
  assert.deepEqual(
    parsed.rows.map((row) => [row.firstName, row.lastName]),
    [["Amina", "Khan"], ["Mary", "Ann Lee"], ["Prince", null]],
  );
});

test("skipped line numbers are file lines even when blank lines come before them", () => {
  const parsed = parseTraineeCsv("email\na@b.uk\n\n\n,x\nnope");
  assert.deepEqual(parsed.skippedLines, [5]);
  assert.deepEqual(parsed.invalidLines, [6]);
});

test("a UTF-8 byte-order mark does not hide the email column", () => {
  const parsed = parseTraineeCsv("﻿email,cohort\na@b.uk,June");
  assert.equal(parsed.error, null);
  assert.equal(parsed.rows[0]?.email, "a@b.uk");
});

test("a semicolon-separated file (Excel in much of Europe) is read as columns", () => {
  const parsed = parseTraineeCsv("email;first name\na@b.uk;Amina");
  assert.equal(parsed.error, null);
  assert.deepEqual(parsed.rows.map((r) => [r.email, r.firstName]), [["a@b.uk", "Amina"]]);
});

test("a repeated address is counted once and its later lines are reported", () => {
  const parsed = parseTraineeCsv("email\na@b.uk\nA@B.uk\nc@d.uk\na@b.uk");
  assert.deepEqual(parsed.rows.map((r) => r.email), ["a@b.uk", "c@d.uk"]);
  assert.deepEqual(parsed.duplicateLines, [3, 5]);
});

test("a missing email column names the columns that were found", () => {
  const parsed = parseTraineeCsv("name;cohort\nAmina;June");
  assert.match(parsed.error ?? "", /found: name, cohort/);
});
