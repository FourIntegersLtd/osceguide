import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { Rating } from "@/capabilities/feedback/rubric";
import {
  fieldValuesFor,
  finishedReviewers,
  reviewersAgreeLine,
  leadSaveNote,
  formDomains,
  initialComments,
  initialRatings,
  machineRating,
  machineSummaryLine,
  ratingChoices,
  ratingVariant,
  summaryDomains,
  unratedRequired,
  type ReviewForm,
} from "@/domains/assess/results/reviewForm";

const RAG: Rating = { kind: "rag", field: "score", scale: ["G", "A", "R"], step: "number" };

/** An SCA-shaped form: two competencies under tasks, one under global skills; tasks required. */
const SCA_FORM: ReviewForm = {
  rubric_version_id: "v1",
  rating: RAG,
  required_domains: ["tasks"],
  fields: [
    { path: "tasks.discovers_ice.score", domain_id: "tasks", domain_label: "Tasks", competency_id: "discovers_ice", label: "Discovers ICE", descriptors: {} },
    { path: "tasks.safety_net.score", domain_id: "tasks", domain_label: "Tasks", competency_id: "safety_net", label: "Safety netting", descriptors: {} },
    { path: "global_skills.score", domain_id: "global_skills", domain_label: "Global skills", competency_id: null, label: "Global skills", descriptors: {} },
  ],
};

describe("review form from the rubric", () => {
  it("groups fields by domain in rubric order and marks the required ones", () => {
    assert.deepEqual(
      formDomains(SCA_FORM).map((domain) => [domain.label, domain.required, domain.fields.length]),
      [
        ["Tasks", true, 2],
        ["Global skills", false, 1],
      ],
    );
  });

  it("names a slot summary's domains from the labels the backend sends", () => {
    assert.deepEqual(
      summaryDomains({
        slot_id: "slot-1",
        completed_reviews: 2,
        by_domain: { tasks: "A", global_skills: "G", data_gathering: "R" },
        domain_labels: { tasks: "Tasks", global_skills: "Global skills" },
      }),
      [
        { id: "tasks", label: "Tasks", value: "A" },
        { id: "global_skills", label: "Global skills", value: "G" },
        { id: "data_gathering", label: "data_gathering", value: "R" },
      ],
    );
    assert.deepEqual(summaryDomains(null), []);
  });

  it("reads saved ratings and notes, dropping values the rating refuses", () => {
    const saved = { "tasks.discovers_ice.score": "A", "global_skills.score": "X", "tasks.comment": "Good ICE" };
    assert.deepEqual(initialRatings(SCA_FORM, saved), { "tasks.discovers_ice.score": "A" });
    assert.deepEqual(initialComments(SCA_FORM, saved), { tasks: "Good ICE" });
    assert.deepEqual(fieldValuesFor({ "tasks.discovers_ice.score": "A" }, { tasks: " Good ICE ", global_skills: "  " }), {
      "tasks.discovers_ice.score": "A",
      "tasks.comment": "Good ICE",
    });
  });

  it("reads the machine's rating at the same dotted path in the payload", () => {
    const payload = { tasks: { discovers_ice: { score: "R", score_explanation: "…" } } };
    assert.equal(machineRating(RAG, payload, "tasks.discovers_ice.score"), "R");
    assert.equal(machineRating(RAG, payload, "tasks.safety_net.score"), null);
  });

  it("names the required domains still unrated", () => {
    assert.deepEqual(unratedRequired(SCA_FORM, {}), ["Tasks"]);
    assert.deepEqual(unratedRequired(SCA_FORM, { "tasks.safety_net.score": "G" }), []);
  });

  it("offers a choice per rating kind", () => {
    assert.deepEqual(ratingChoices(RAG), ["G", "A", "R"]);
    assert.deepEqual(ratingChoices({ kind: "boolean", field: "competent", step: "number" }), [true, false]);
    assert.deepEqual(ratingChoices({ kind: "range", field: "score", minimum: 0, maximum: 4, step: "integer" }), [4, 3, 2, 1, 0]);
    // 0 to 50 is a number field, not fifty-one buttons; so is a decimal range.
    assert.equal(ratingChoices({ kind: "range", field: "score", minimum: 0, maximum: 50, step: "integer" }), null);
    assert.equal(ratingChoices({ kind: "range", field: "score", minimum: 0, maximum: 4, step: "number" }), null);
  });

  it("colours a rating by position or fraction, never by letter", () => {
    const words: Rating = { kind: "scale", field: "score", scale: ["Excellent", "Pass", "Borderline", "Fail"], step: "number" };
    assert.deepEqual(["Excellent", "Pass", "Fail", "Nope"].map((value) => ratingVariant(words, value)), ["success", "warning", "danger", "neutral"]);
    assert.deepEqual(["G", "A", "R"].map((value) => ratingVariant(RAG, value)), ["success", "warning", "danger"]);
    const range: Rating = { kind: "range", field: "score", minimum: 0, maximum: 4, step: "number" };
    assert.deepEqual([4, 2, 1].map((value) => ratingVariant(range, value)), ["success", "warning", "danger"]);
    assert.equal(ratingVariant(null, "G"), "neutral");
  });
});

describe("leadSaveNote", () => {
  it("names what the backend stored", () => {
    assert.equal(leadSaveNote("completed"), "Review completed.");
    assert.equal(leadSaveNote("draft"), "Draft saved.");
  });
});

describe("the reviewers of a slot", () => {
  const scale: Rating = { kind: "rag", field: "score", scale: ["G", "A", "R"] } as Rating;
  it("lists finished reviews by name with their overall rating, and leaves drafts out", () => {
    const items = [
      { status: "completed", reviewer_name: "Dr Patel", overall: "G" },
      { status: "draft", reviewer_name: null, overall: null },
      { status: "completed", reviewer_name: "Ms Clarke", overall: "R" },
    ];
    assert.deepEqual(finishedReviewers(items, scale), [
      { name: "Dr Patel", rating: "Green" },
      { name: "Ms Clarke", rating: "Red" },
    ]);
  });
  it("says whether they agree only when two have finished", () => {
    assert.equal(reviewersAgreeLine(true), "Reviewers agree.");
    assert.equal(reviewersAgreeLine(false), "Reviewers disagree. The lower rating is the one shown.");
    assert.equal(reviewersAgreeLine(null), null);
  });
});

describe("machineSummaryLine", () => {
  it("lists the machine's rating per domain, read at the domain's own field", () => {
    const form: ReviewForm = {
      rubric_version_id: "v1",
      rating: RAG,
      required_domains: [],
      fields: [
        { path: "history.score", domain_id: "history", domain_label: "History taking", competency_id: null, label: "History taking", descriptors: {} },
        { path: "comms.score", domain_id: "comms", domain_label: "Communication", competency_id: null, label: "Communication", descriptors: {} },
        { path: "comms.rapport.score", domain_id: "comms", domain_label: "Communication", competency_id: "rapport", label: "Rapport", descriptors: {} },
      ],
    } as ReviewForm;
    const payload = { history: { score: "G" }, comms: { score: "A", rapport: { score: "R" } } };
    assert.equal(machineSummaryLine(form, payload), "History taking: Green · Communication: Amber");
    assert.equal(machineSummaryLine(form, null), "");
  });
});
