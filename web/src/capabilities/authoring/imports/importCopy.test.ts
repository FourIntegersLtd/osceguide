import assert from "node:assert/strict";
import test from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { importStatusChip, importStatusLine, uploadFailureMessage } from "@/capabilities/authoring/imports/importCopy";

const refusal = (status: number, code: string) =>
  new PlatformError(status, { code, message: "raw server text" } as never);

test("an unreadable file is named, whatever the server wrote", () => {
  assert.equal(
    uploadFailureMessage(refusal(422, "invalid_import_file")),
    "It is not a PDF or Word file we can read, or it has nothing in it.",
  );
});

test("a rate limit says to wait", () => {
  assert.equal(
    uploadFailureMessage(refusal(429, "too_many_requests")),
    "Too many imports just now. Wait a minute and upload the rest again.",
  );
});

test("any other refusal keeps the server's message", () => {
  assert.equal(uploadFailureMessage(refusal(409, "conflict")), "raw server text");
});

test("a drafted template that is not published says creating the station publishes it", () => {
  assert.match(importStatusLine("template_ready", false), /creating the station also publishes the template/);
  assert.equal(
    importStatusLine("template_ready", true),
    "Template drafted. Review it, then create the station.",
  );
});

test("the pill beside an import says working or failed, and nothing when it is done", () => {
  assert.equal(importStatusChip("drafting_template"), null);
  assert.equal(importStatusChip("failed"), "Failed");
  assert.equal(importStatusChip("completed"), null);
});
