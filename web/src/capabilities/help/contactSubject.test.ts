import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { contactSubjectText } from "@/capabilities/help/contactSubject";

describe("contactSubjectText", () => {
  it("sends the label of a listed subject and ignores the Other text", () => {
    assert.equal(contactSubjectText("problem", "ignored"), "Problem with a station or session");
    assert.equal(contactSubjectText("general", ""), "General enquiry");
  });

  it("sends the trimmed text for Other, empty until typed", () => {
    assert.equal(contactSubjectText("other", "  Billing  "), "Billing");
    assert.equal(contactSubjectText("other", "  "), "");
  });

  it("is empty before a choice", () => {
    assert.equal(contactSubjectText("", "x"), "");
  });
});
