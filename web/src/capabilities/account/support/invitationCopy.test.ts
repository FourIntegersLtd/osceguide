import assert from "node:assert/strict";
import { test } from "node:test";
import { invitationView, invitationSubtitle } from "@/capabilities/account/support/invitationCopy";

test("the subtitle names the organisation that invited the person", () => {
  assert.equal(
    invitationSubtitle("Ashford Medical School"),
    "Ashford Medical School has invited you. Choose a password to join.",
  );
});

test("with no organisation the subtitle keeps the current copy", () => {
  assert.equal(invitationSubtitle(null), "Your organisation has invited you. Choose a password to join.");
});

test("an employer invitation names the organisation and the candidate role", () => {
  assert.deepEqual(invitationView({ organisationName: "Acme Health Trust", orgType: "employer", role: "trainee" }), {
    title: "Acme Health Trust invited you",
    subtitle: "You are joining as a candidate. Choose a password to see your assessment.",
    action: "Join Acme Health Trust",
  });
});

test("an employer invitation to mark says assessor", () => {
  const view = invitationView({ organisationName: "Acme Health Trust", orgType: "employer", role: "supervisor" });
  assert.equal(view.subtitle, "You are joining as an assessor. You will mark candidates on the stations you are given.");
  assert.equal(view.action, "Join as an assessor");
});

test("an employer invitation to run the organisation says administrator", () => {
  const view = invitationView({ organisationName: "Acme Health Trust", orgType: "employer", role: "admin" });
  assert.equal(view.subtitle, "You are joining as an administrator. Choose a password to manage your organisation.");
});

test("an institution invitation says trainee, supervisor and administrator", () => {
  const view = (role: string) => invitationView({ organisationName: "Ashford Medical School", orgType: "university", role });
  assert.equal(view("trainee").subtitle, "You are joining as a trainee. Choose a password to join.");
  assert.equal(view("supervisor").subtitle, "You are joining as a supervisor. Choose a password to join.");
  assert.equal(view("admin").subtitle, "You are joining as an administrator. Choose a password to join.");
  assert.equal(view("trainee").title, "Join Ashford Medical School");
  assert.equal(view("trainee").action, "Accept invitation");
});

test("without a kind or role the page keeps its current copy", () => {
  assert.deepEqual(invitationView({ organisationName: "Ashford Medical School", orgType: null, role: null }), {
    title: "Join Ashford Medical School",
    subtitle: "Ashford Medical School has invited you. Choose a password to join.",
    action: "Accept invitation",
  });
  assert.deepEqual(invitationView({ organisationName: null, orgType: null, role: null }), {
    title: "Accept your invitation",
    subtitle: "Your organisation has invited you. Choose a password to join.",
    action: "Accept invitation",
  });
});
