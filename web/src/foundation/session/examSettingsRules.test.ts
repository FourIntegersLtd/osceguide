import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { ExamSettings } from "@/foundation/session/useCurrentExam";
import {
  hasStationSubtypes,
  helpModeChoice,
  offersPatientPractice,
  showsMarkingTips,
} from "@/foundation/session/examSettingsRules";

/** A whole `ExamSettings`, so each test only overrides the field it is about. */
const settings = (over: Partial<ExamSettings> = {}): ExamSettings => ({
  date_label: "Exam date",
  peer_waiting_email: false,
  show_tips_while_marking: false,
  ...over,
});

describe("helpModeChoice", () => {
  it("offers a choice only when both modes are listed", () => {
    assert.deepEqual(helpModeChoice(settings({ help_modes: ["navigate", "knowledge_base"] })), {
      offersChoice: true,
      opensDirectlyOnKnowledge: false,
    });
  });

  it("opens straight into the knowledge base when that is the only mode", () => {
    assert.deepEqual(helpModeChoice(settings({ help_modes: ["knowledge_base"] })), {
      offersChoice: false,
      opensDirectlyOnKnowledge: true,
    });
  });

  it("defaults to navigate-only, with no choice screen, when nothing is set", () => {
    assert.deepEqual(helpModeChoice(settings({})), {
      offersChoice: false,
      opensDirectlyOnKnowledge: false,
    });
  });
});

describe("offersPatientPractice", () => {
  it("is true when practice_as_patient is one of the listed modes", () => {
    assert.equal(offersPatientPractice(settings({ session_modes: ["debrief", "practice_as_patient"] })), true);
  });

  it("is false for a debrief-only exam", () => {
    assert.equal(offersPatientPractice(settings({ session_modes: ["debrief"] })), false);
  });

  it("defaults to true when the exam does not say, matching the backend default", () => {
    assert.equal(offersPatientPractice(settings({})), true);
  });
});

describe("showsMarkingTips", () => {
  it("reads the flag literally, with no exam-code guess", () => {
    assert.equal(showsMarkingTips(settings({ show_tips_while_marking: true })), true);
    assert.equal(showsMarkingTips(settings({ show_tips_while_marking: false })), false);
  });
});

describe("hasStationSubtypes", () => {
  it("is true once the exam lists at least one sub-type", () => {
    assert.equal(
      hasStationSubtypes(
        settings({
          station_subtypes: [{ key: "interview", label: "Interview", generation_profile: "interview" }],
        }),
      ),
      true,
    );
  });

  it("is false for an exam with no sub-types, or none set at all", () => {
    assert.equal(hasStationSubtypes(settings({ station_subtypes: [] })), false);
    assert.equal(hasStationSubtypes(settings({})), false);
  });
});
