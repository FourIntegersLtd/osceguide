import assert from "node:assert/strict";
import { test } from "node:test";
import { passwordSchema } from "@/capabilities/account/support/validateAuthForm";

test("a password needs two kinds of character, as the server says, not only twelve", () => {
  const issue = (value: string) => passwordSchema.safeParse(value).error?.issues[0]?.message ?? null;
  assert.equal(issue("aaaaaaaaaaaa"), "Mix letters with numbers, punctuation, or capitals");
  assert.equal(issue("short1A"), "Use at least 12 characters");
  assert.equal(issue("Aaaaaaaaaaaa"), null);
});
