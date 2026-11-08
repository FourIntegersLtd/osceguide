import assert from "node:assert/strict";
import test from "node:test";
import { assessWordsFor } from "@/capabilities/assess-words/vocabulary";
import { audienceMeta, roleMeta, rolesForAudience, stationAudiences } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";

test("institution labels are unchanged", () => {
  assert.equal(audienceMeta("examiner").label, "Examiner");
  assert.equal(roleMeta("examiner").label, "Examiner notes");
  assert.equal(audienceMeta("faculty").description.includes("learner"), true);
  assert.deepEqual(stationAudiences().map((a) => a.label), ["Patient", "Candidate brief", "Examiner", "Faculty"]);
});

test("hire says assessor and candidate", () => {
  const hire = assessWordsFor("hire");
  assert.equal(audienceMeta("examiner", hire).label, "Assessor only");
  assert.equal(audienceMeta("candidate", hire).label, "Candidate sees it");
  assert.equal(audienceMeta("patient", hire).label, "Patient");
  assert.deepEqual(stationAudiences(hire).map((a) => a.label), ["Patient", "Candidate sees it", "Assessor only", "Faculty"]);
  assert.equal(audienceMeta("examiner", hire).description, "Model answers and marking notes for the assessor after the station.");
  assert.equal(roleMeta("examiner", hire).label, "Assessor notes");
  assert.equal(rolesForAudience("examiner", hire)[0]?.label, "Assessor notes");
  assert.equal(audienceMeta("faculty", hire).description.includes("learner"), false);
});
