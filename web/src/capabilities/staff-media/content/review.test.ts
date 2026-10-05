import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  acceptSuggestion,
  dismissSuggestion,
  reopenSuggestion,
  firstOpenStep,
  isChecked,
  reviewSteps,
  reviewOf,
  scriptGroups,
  setScriptLine,
  spokenLines,
} from "@/capabilities/staff-media/content/review";
import type { FactClaim } from "@/capabilities/fact-check/facts";

const DECK_LINES = [
  "Here is the reading that matters.",
  "[chuckles] Kwame's monitor averaged one fifty-two over ninety-six.",
  "Now, how do we stage it?",
  "Three things to take away.",
  "Confirm the diagnosis at home.",
  "That is new hypertension.",
];

function deck(): Record<string, unknown> {
  return {
    slides: [
      {
        title: "Kwame's readings",
        bullets: ["Stage 2 is a clinic reading of 150/95 or more"],
        source_notes: "Clinic 150/95.",
        narration: { intro: DECK_LINES[0], items: [DECK_LINES[1]] },
      },
    ],
    presentation: {
      sections: [{ before: 2, title: "Staging", line: DECK_LINES[2] }],
      recap_intro: DECK_LINES[3],
      takeaways: [{ text: "Confirm at home", line: DECK_LINES[4] }],
      signoff: DECK_LINES[5],
    },
    review: { script: { lines: DECK_LINES, issues: [], changes: [] } },
  };
}

const CLAIM: FactClaim = {
  id: "claim-1",
  slide: 1,
  claim: "Stage 2 is a clinic reading of 150/95 or more",
  verdict: "contradicted",
  why: "NG136 says 160/100.",
  checked: ["guidelines"],
  evidence: [],
  suggestion: { old: "150/95", new: "160/100" },
};

describe("the staff review of a spoken item", () => {
  it("speaks a deck's slides and then its framing, in the server's order", () => {
    assert.deepEqual(spokenLines("slide_deck", deck()), DECK_LINES);
    assert.equal(isChecked("slide_deck", deck()), true);
  });

  it("speaks nothing until every slide is narrated", () => {
    const content = deck();
    (content.slides as Record<string, unknown>[])[0]!.narration = undefined;
    assert.deepEqual(spokenLines("slide_deck", content), []);
    assert.equal(isChecked("slide_deck", content), false);
  });

  it("splits a dialogue as the server does", () => {
    const script =
      '**Ben:** Chest pain on  exertion needs an "ECG".\n\nMichelle: And a same-day review.';
    assert.deepEqual(spokenLines("podcast", { script }), [
      "Ben: Chest pain on exertion needs an ECG.",
      "Michelle: And a same-day review.",
    ]);
  });

  it("is no longer checked once a line is edited", () => {
    const groups = scriptGroups("slide_deck", deck());
    const edited = setScriptLine(deck(), groups[0]!, 2, "Kwame averaged 152 over 96.");
    assert.deepEqual(
      (edited.slides as { narration: { items: string[] } }[])[0]!.narration.items,
      ["Kwame averaged 152 over 96."],
    );
    assert.equal(isChecked("slide_deck", edited), false);
  });

  it("edits the framing line it was asked to", () => {
    const groups = scriptGroups("slide_deck", deck());
    const edited = setScriptLine(deck(), groups[1]!, 4, "That is it.");
    assert.deepEqual(spokenLines("slide_deck", edited).slice(2), [
      DECK_LINES[2],
      DECK_LINES[3],
      DECK_LINES[4],
      "That is it.",
    ]);
  });

  it("edits one turn of a dialogue and keeps who says it", () => {
    const content = { script: "Ben: One.\n\nMichelle: Two." };
    const edited = setScriptLine(content, scriptGroups("podcast", content)[0]!, 2, "Three.");
    assert.equal(edited.script, "Ben: One.\n\nMichelle: Three.");
  });

  it("accepting a correction changes the slide's source and not what was spoken", () => {
    const content = {
      ...deck(),
      review: { facts: { checked_at: "t", claims: [CLAIM] } },
    };
    const accepted = acceptSuggestion(content, CLAIM, { from: CLAIM.suggestion!.old!, to: "160/100" });
    const slide = (accepted.slides as Record<string, unknown>[])[0]!;
    assert.deepEqual(slide.bullets, ["Stage 2 is a clinic reading of 160/100 or more"]);
    assert.equal(slide.source_notes, "Clinic 160/100.");
    assert.deepEqual(slide.narration, { intro: DECK_LINES[0], items: [DECK_LINES[1]] });
    assert.equal(reviewOf(accepted).facts?.claims[0]?.decision, "accepted");
  });

  it("dismissing a correction changes nothing but the decision", () => {
    const content: Record<string, unknown> = {
      ...deck(),
      review: { facts: { checked_at: "t", claims: [CLAIM] } },
    };
    const dismissed = dismissSuggestion(content, CLAIM);
    assert.deepEqual(dismissed.slides, content.slides);
    assert.equal(reviewOf(dismissed).facts?.claims[0]?.decision, "dismissed");
  });

  it("reopening an accepted correction puts the original words back and needs a ruling again", () => {
    const content: Record<string, unknown> = {
      ...deck(),
      review: { facts: { checked_at: "t", claims: [CLAIM] } },
    };
    const accepted = acceptSuggestion(content, CLAIM, { from: CLAIM.suggestion!.old!, to: "160/100" });
    const claim = reviewOf(accepted).facts!.claims[0]!;
    const reopened = reopenSuggestion(accepted, claim);
    assert.deepEqual(reopened.slides, content.slides);
    assert.equal(reviewOf(reopened).facts?.claims[0]?.decision, undefined);
    assert.equal(reviewOf(reopened).facts?.claims[0]?.swap, undefined);
  });

  it("reopening a kept claim changes nothing but the decision", () => {
    const content: Record<string, unknown> = {
      ...deck(),
      review: { facts: { checked_at: "t", claims: [CLAIM] } },
    };
    const dismissed = dismissSuggestion(content, CLAIM);
    const reopened = reopenSuggestion(dismissed, reviewOf(dismissed).facts!.claims[0]!);
    assert.deepEqual(reopened.slides, content.slides);
    assert.equal(reviewOf(reopened).facts?.claims[0]?.decision, undefined);
  });

  it("walks a deck through its steps", () => {
    assert.equal(firstOpenStep("slide_deck", { slides: [] }), "draft");
    // Just written from a brief: read the draft before checking it.
    assert.equal(firstOpenStep("slide_deck", { ...deck(), review: undefined }), "draft");
    // Written and its script checked, but its facts never looked at.
    assert.equal(firstOpenStep("slide_deck", deck()), "facts");
    const contradicted = {
      ...deck(),
      review: {
        script: { lines: DECK_LINES, issues: [], changes: [] },
        facts: { checked_at: "t", claims: [CLAIM] },
      },
    };
    assert.deepEqual(
      reviewSteps("slide_deck", contradicted).map((step) => [step.id, step.state, step.note]),
      [
        ["draft", "done", "Written"],
        ["facts", "attention", "1 to resolve"],
        ["script", "done", "Checked"],
        ["voice", "todo", "Not voiced"],
      ],
    );
    const ruled = dismissSuggestion(contradicted, CLAIM);
    assert.equal(firstOpenStep("slide_deck", ruled), "voice");
    const voiced = { ...ruled, final_video_url: "https://cdn/x.mp4", status: "completed" };
    assert.equal(reviewSteps("slide_deck", voiced)[3]!.state, "done");
    // Written again after voicing: the video no longer says what the script does.
    assert.equal(
      reviewSteps("slide_deck", { ...voiced, status: "awaiting_review" })[3]!.state,
      "todo",
    );
  });
});

describe("the agent's run", () => {
  it("reads the steps, what it used and what it left, and an agent fix undoes like a reader's", () => {
    const content = {
      slides: [{ title: "HRT", bullets: ["Estradiol patch 50 micrograms"] }],
      review: {
        brief: { brief: "Teach HRT." },
        run: {
          steps: [{ at: "t", tool: "check_facts", summary: "1 contradicted" }],
          tokens: 700,
          outcome: "finished",
          open: ["Corrected (slide 1, claim-1)"],
        },
        facts: {
          checked_at: "t",
          claims: [
            {
              id: "claim-1",
              slide: 1,
              claim: "Estradiol patch 500 micrograms",
              verdict: "contradicted",
              decision: "accepted",
              by: "agent",
              swap: { from: "500 micrograms", to: "50 micrograms" },
            },
          ],
        },
      },
    };

    const review = reviewOf(content);
    assert.deepEqual(review.run, {
      steps: [{ at: "t", tool: "check_facts", summary: "1 contradicted" }],
      tokens: 700,
      outcome: "finished",
      summary: "",
      open: ["Corrected (slide 1, claim-1)"],
      stop: false,
    });
    assert.deepEqual(review.brief, { brief: "Teach HRT." });
    // A run from before the case had its own box shows the case under the brief.
    const older = reviewOf({ review: { brief: { brief: "Teach HRT.", source_text: "Mrs X, 52." } } });
    assert.deepEqual(older.brief, { brief: "Teach HRT.\n\nMrs X, 52." });
    const undone = reopenSuggestion(content, review.facts!.claims[0]!);
    assert.deepEqual((undone.slides as { bullets: string[] }[])[0]!.bullets, [
      "Estradiol patch 500 micrograms",
    ]);
  });

  it("labels a fact check a person did themselves", () => {
    const byHand = {
      ...deck(),
      review: {
        script: { lines: DECK_LINES, issues: [], changes: [] },
        facts: { checked_at: "t", checked_by: "staff-1", claims: [{ ...CLAIM, verdict: "supported" }] },
      },
    };
    assert.deepEqual(reviewSteps("slide_deck", byHand)[1], {
      id: "facts",
      label: "Check facts",
      state: "done",
      note: "1 claims checked by hand",
    });
  });
});
