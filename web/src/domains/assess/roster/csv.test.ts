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
  assert.deepEqual(parsed.skippedLines, [3, 4]);
  assert.equal(parsed.error, null);
});

test("addresses are lowercased, so a re-import matches what is already there", () => {
  const parsed = parseTraineeCsv("email\nAmina@NHS.uk");
  assert.equal(parsed.rows[0]?.email, "amina@nhs.uk");
});
