import assert from "node:assert/strict";
import test from "node:test";
import { setupRequestBody } from "@/domains/assess/newOrganisationRequest";

test("files a contact message staff can act on", () => {
  assert.deepEqual(
    setupRequestBody({
      name: "Acme Clinics",
      orgType: "Employer",
      exams: ["PLAB 2"],
      purposes: ["Recruitment", "Onboarding"],
      ownerName: "Dana Lee",
      email: "dana@acme.test",
    }),
    {
      kind: "contact",
      name: "Dana Lee",
      email: "dana@acme.test",
      subject: "Set up an organisation: Acme Clinics",
      source: "register/organisation",
      body: [
        "Organisation: Acme Clinics",
        "Type: Employer",
        "Exams: PLAB 2",
        "Use: Recruitment, Onboarding",
        "Contact: Dana Lee <dana@acme.test>",
      ].join("\n"),
    },
  );
});

test("says when no exam was chosen", () => {
  const { body } = setupRequestBody({
    name: "X",
    orgType: "Deanery",
    exams: [],
    purposes: ["CPD"],
    ownerName: "A",
    email: "a@x.test",
  });
  assert.match(body, /Exams: none chosen/);
});
