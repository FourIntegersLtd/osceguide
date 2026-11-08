import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_REGISTER, REGISTER_PATHS, employerRequestBody, setupRequestBody } from "@/domains/assess/newOrganisationRequest";

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

test("the employer path files an Employer request for Recruitment with the volume as a note", () => {
  const request = employerRequestBody({ name: "Acme Health Trust", ownerName: "Sam Okafor", email: "sam.okafor@acme.nhs.uk", candidatesPerYear: " 120 " });
  assert.equal(request.subject, "Set up an organisation: Acme Health Trust");
  assert.equal(
    request.body,
    ["Organisation: Acme Health Trust", "Type: Employer", "Use: Recruitment", "Contact: Sam Okafor <sam.okafor@acme.nhs.uk>", "Notes: Candidates a year: 120"].join("\n"),
  );
  assert.equal(employerRequestBody({ name: "A", ownerName: "B", email: "b@a.test" }).body.includes("Notes"), false);
});

test("the employer register words follow the board", () => {
  assert.deepEqual(REGISTER_PATHS.map((p) => p.label), ["A school or deanery", "An employer"]);
  assert.deepEqual(EMPLOYER_REGISTER.sent("Acme Health Trust", "sam.okafor@acme.nhs.uk"), {
    title: "Request sent",
    heading: "We will email you",
    body: "We have your request for Acme Health Trust. Look for an email to sam.okafor@acme.nhs.uk within one working day; it has a link to finish setting up.",
    link: "See what your account looks like",
  });
  assert.deepEqual(EMPLOYER_REGISTER.failed, { title: "That did not send", body: "Check your connection and press Send request again. Nothing was saved." });
});
