import assert from "node:assert/strict";
import { test } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { contactEmailLooksValid, organisationChanges, organisationFailure, organisationLead, organisationSaveLabel, orgTabLabels, planLine } from "@/domains/assess/settings/hireSettings";

test("an employer's tabs are Sign-in and Automatic user sync, an institution's keep their names", () => {
  assert.deepEqual(orgTabLabels(EMPLOYER_WORDS), { sso: "Sign-in", provisioning: "Automatic user sync" });
  assert.deepEqual(orgTabLabels(INSTITUTION_WORDS), { sso: "Single sign-on", provisioning: "Provisioning" });
});

test("the Organisation card lead and Save label pin both literals", () => {
  assert.equal(organisationLead(EMPLOYER_WORDS), "Your organisation's web address cannot be changed here. Email support to change it.");
  assert.equal(organisationLead(INSTITUTION_WORDS), "The web address is fixed. Contact support to change it.");
  assert.equal(organisationSaveLabel(EMPLOYER_WORDS), "Save changes");
  assert.equal(organisationSaveLabel(INSTITUTION_WORDS), "Save name");
});

test("the plan line states only what the api knows", () => {
  assert.equal(planLine({}, () => "x"), "Employer");
  assert.equal(planLine({ contract_ends_at: "2026-12-01" }, () => "1 Dec"), "Employer · contract runs to 1 Dec");
  assert.equal(planLine({ candidate_seats: 120 }, () => "x"), "Employer · 120 candidate seats");
  assert.equal(planLine({ candidate_seats: 120 }, () => "x", 58), "Employer · 120 candidate seats, 58 used");
  assert.equal(planLine({ candidate_seats: 120, contract_ends_at: "2026-12-01" }, () => "1 Dec", 58), "Employer · 120 candidate seats, 58 used · contract runs to 1 Dec");
  assert.equal(planLine({}, () => "x", 58), "Employer");
});

const ACME = { name: "Acme", contact_email: "hr@acme.test" };

test("an employer's save sends only what changed; a cleared contact is null", () => {
  assert.deepEqual(organisationChanges(ACME, { name: "Acme", contactEmail: "people@acme.test" }, EMPLOYER_WORDS), { contact_email: "people@acme.test" });
  assert.deepEqual(organisationChanges(ACME, { name: " Acme Trust ", contactEmail: "hr@acme.test" }, EMPLOYER_WORDS), { name: "Acme Trust" });
  assert.deepEqual(organisationChanges(ACME, { name: "Acme", contactEmail: "  " }, EMPLOYER_WORDS), { contact_email: null });
  assert.equal(organisationChanges(ACME, { name: "Acme", contactEmail: "hr@acme.test" }, EMPLOYER_WORDS), null);
  assert.equal(organisationChanges({ name: "Acme" }, { name: "Acme", contactEmail: "" }, EMPLOYER_WORDS), null);
});

test("an institution's save is the name alone", () => {
  assert.deepEqual(organisationChanges(ACME, { name: "Acme 2", contactEmail: "x@y.test" }, INSTITUTION_WORDS), { name: "Acme 2" });
  assert.equal(organisationChanges(ACME, { name: "Acme", contactEmail: "x@y.test" }, INSTITUTION_WORDS), null);
});

test("the contact email only has to look like an email, or be empty", () => {
  assert.equal(contactEmailLooksValid(""), true);
  assert.equal(contactEmailLooksValid("hr@acme.test"), true);
  assert.equal(contactEmailLooksValid("hr@acme"), false);
  assert.equal(contactEmailLooksValid("not an email"), false);
});

test("a refused contact email gets its own words, other failures the fallback", () => {
  const refused = new PlatformError(422, { code: "invalid_input", message: "The request was not valid" });
  assert.equal(organisationFailure(refused, { contact_email: "a@b.c" }, () => "fallback"), "That contact email does not look right. Check it and try again.");
  assert.equal(organisationFailure(refused, { name: "X" }, () => "fallback"), "fallback");
});
