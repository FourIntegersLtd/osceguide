import assert from "node:assert/strict";
import test from "node:test";
import { setupRequestBody } from "@/domains/assess/newOrganisationRequest";

const base = {
  name: "Acme Clinics",
  orgType: "Employer",
  purposes: ["Recruitment", "Onboarding"],
  ownerName: "Dana Lee",
  email: "dana@acme.test",
};

test("files a contact message staff can act on, with no exams line", () => {
  assert.deepEqual(setupRequestBody(base), {
    kind: "contact",
    name: "Dana Lee",
    email: "dana@acme.test",
    subject: "Set up an organisation: Acme Clinics",
    source: "register/organisation",
    body: [
      "Organisation: Acme Clinics",
      "Type: Employer",
      "Use: Recruitment, Onboarding",
      "Contact: Dana Lee <dana@acme.test>",
    ].join("\n"),
  });
});

test("adds a Notes line when notes are given", () => {
  const { body } = setupRequestBody({ ...base, notes: "  40 trainees, start in March  " });
  assert.equal(body.split("\n").at(-1), "Notes: 40 trainees, start in March");
});

test("leaves out Notes when blank", () => {
  assert.doesNotMatch(setupRequestBody({ ...base, notes: "   " }).body, /Notes/);
  assert.doesNotMatch(setupRequestBody(base).body, /Notes/);
});
