# Rubric feedback, dashboards and review forms

## Sub-features
- The learner's feedback on a marked attempt (`RubricFeedback`), drawn from the attempt's own rubric.
- The learner dashboard `/app/me/dashboard`, whose titles, pass lines and bands come from the rubric's display.
- The examiner's slot review (`/app/<org>/slots/<slot>/review?attempt=<id>`): a form generated from
  `ReviewFormRead`, the GP lead's review, "What the reviewers agreed", and the machine's marking beside them.
- The staff inspector `/staff/attempts/<id>` (its Feedback panel), and the sitting results / candidate card.

## How to get to it (user POV)
Consumer: Practice → a marked station → Feedback tab, or Dashboard. Institution: Sittings → a sitting →
a candidate's station → Review.

## Driving it with playwright-core
```js
await open(run, `/app/me/attempts/${attemptId}`);   // redirects to .../practise?action=review&tab=feedback
// e.g. SCA "of ratings at G"; PLAB "Pass at 7/12"; CASC "Pass at 80%"; Ortho "18/50", "Pass at 35/50"
await open(run, "/app/me/dashboard");               // SCA "Where you stand"; PLAB "Pass (7/12)"; Ortho "0–17"
await open(run, `/app/verify-rubrics/slots/${slot}/review?attempt=${copy}`);
// "Your marking", "Required", "machine: G"; SCA buttons G/A/R, Ortho 10..0, CASC Met / Not met, PLAB spinbutton
```
Chart text lives in SVG: read `main svg text` as well as `main`'s innerText.

## Gotchas
- **Local data.** Use `e2e-marking-3@example.com`, which holds marked attempts for all four exams. Then:
  - Set `users.exam_code` to the exam you are checking, or `/app/me/**` shows the exam picker. Reset it to
    NULL afterwards.
  - The dashboard follows that one exam.
- **No marked attempts locally (2026-10-06).** `feedback-fixture.sql`'s attempt ids no longer exist. Use
  `marked-slot-fixture.sql` (self-contained, walkthrough@example.com, org `verify-b53`): one marked SCA
  practice attempt and one marked exam-slot attempt; `marked-slot-teardown.sql` removes it.
- **Whose mark.** `RubricFeedback` heads the learner's view "Your mark" and the examiner's review
  "Automatic marking" (`heading` prop, B53).
- **Institution screens.** They need an org whose slots carry marked `exam_slot` attempts.
  `feedback-fixture.sql` builds one (`verify-rubrics`), and `feedback-teardown.sql` removes it. Run both
  with `docker exec -i platform-api-postgres-1 psql -U postgres -d osce_platform < file`.
- **`/staff` needs a platform admin.** None is seeded locally. Set `is_platform_admin` on the test account
  for the run, then unset it.
- **Expected errors, not bugs:**
  - 404 on `reviews/mine` and `gp-lead-review` before anyone has reviewed;
  - 422 `not_an_exam_sitting` on `/cohort` for a training sitting.
  The harness counts these as problems and exits 1. Read its "problems:" line.
- **The GP-lead save.** "Draft saved." / "Review completed." stays after a save and a second save carries the
  new revision (fixed 2026-09-30, R-3; `.verify/gp-lead-saved-note.mjs`). The lead's panel is the second
  "Save draft" button and the second "Notes" box on the page.
- **A review screen needs no marking.** A slot with a station version and no attempt renders the reviewer and
  lead forms from the sitting's rubric; see `rubric-builder.md` for a fixture that needs no marked attempts.
