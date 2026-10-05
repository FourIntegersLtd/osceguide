---
name: make-slide-deck
description: Turn an OSCE case (e.g. from the native mock PDF) into a voiced, fact-checked teaching slide deck and publish it to staging, production and legacy Firestore, through platform-api's staff media routes. Use when asked to make, voice or publish slide decks or teaching videos.
---

# Make a slide deck

The pipeline that made decks 1 to 40. Scripts are in `scripts/` next to this
file; run them from there. Working files live in `slide-scripts/work/`
(local, not in git), and finished decks live in `slide-scripts/<nn>-<slug>.json` + `.mp4`.
`slide-scripts/` is the source of truth. Deck `k` is its number; `work/published.txt`
lists what is live, so the next free number is one above the highest there.

## Rules (never break)

- Only platform-api's staff media routes, on the **local** api
  (`PLATFORM_API_URL`, default `http://127.0.0.1:8012`). Never `cb_ask.py`,
  `cb_web.py` or `regenerate_slides.py`. Never deploy Clinical Buddy.
- Sign in only as `walkthrough@example.com` (`signin.mjs`), never a real person.
- Never read `.env`, never print a key. The Firebase key is `service-key` at the repo root,
  used only through `FIREBASE_SERVICE_ACCOUNT_KEY_PATH` inside `pub.sh`.
- Never bypass the api's 409 "script not checked" refusal. Voice only what `chk.sh` passes.
- No direct DB writes. Don't commit or push unless asked. Never edit `livekit/`.

## Prerequisites (check once)

```bash
curl -sf http://127.0.0.1:8012/health || (cd api && make start)   # local api, with its worker running
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:$PATH"
railway whoami                                                     # pub.sh needs it
```

If the api or worker is down and you cannot start it, stop and report; do not work around it.

## Content rules

- **Take only the diagnosis and the relevant management from the source.** The PDF
  case is a rough guide, nothing more. Invent the case yourself: who rings and why,
  the patient (name, age, sex, job, family, setting), the presenting story, the
  history answers, the results and their numbers, the medicines, and the ICE.
  Check the management against NICE/CKS and explain it in your own words.
  The test: someone who reads the PDF case and then watches the deck should NOT be
  able to tell the deck came from it. If a detail is in the PDF, change it or drop it.
- **Never verbatim**: write every line in your own words, never copying phrasing,
  explanations or management lists from the source PDF.
- **Real-world twists**: one "The Twist" slide with 2 to 4 details that are NOT in the
  source case, unique to this deck (not reused from earlier decks), and that change
  the plan (who is at home, work, driving, a hidden medicine, a relative). List them for sign-off.
- **Remote consultations are telephone, never video.** A video case becomes
  telephone, or face-to-face where an examination is needed.
- **Vary the opening.** Never "Welcome to this interactive case". Rotate: a patient
  quote, a scene in the moment, a number or result, a question to the learner, the
  key test or phrase. Check `work/spec*.py` slide 1s so consecutive decks differ.
- **Every slide has a photo** (an S3 picture name). Voice: Ben (the api default).
- Keep Ben's light asides and audio tags such as [chuckles] (the user asked for them twice).
  Fix only what is wrong: facts, and anything that breaks the setting ("in the chair" on a call).
- UK practice: NICE/CKS, DVLA, 999/111, suspected cancer pathway.

## Spec format (`work/spec<k>.py`)

```python
TITLE = "Facial Droop: Stroke or Bell's Palsy?"
SPECIALTY = "Neurology"
ABOUT = "In this video, you'll take a telephone call from ..., covering ..."
SLIDES = [  # (title, picture, bullets|None, highlights|None, narration[, "pause"])
    ("Raise Your Eyebrows", "bells_palsy", None, None, "<varied opener>"),
    ("Clinical Scenario", "telephone_handset", [...], [...], "..."),
    ("What Would You Ask?", "consultation", None, None, "... Pause and list your questions.", "pause"),
    ...
]
```

Shape (15 to 17 slides): opener · Clinical Scenario · (results, if any) · What Would
You Ask? (pause) · Focused History · What They Tell You · The Twist · question (pause) ·
diagnosis · Ideas, Concerns and Expectations · What Would You Do? (pause) · one or two
plan slides · Explaining It to <name> · Learning Points ("Five things to take away") ·
Conclusion & Summary. Highlights must be substrings of their bullets. Copy a recent
`work/spec*.py` as the template.

## Pictures

Names resolve to `https://osceguide.s3.eu-west-2.amazonaws.com/teaching_videos/v2/pictures/<name>.jpg`.
Existing ones: `ls api/app/features/media_production/assets/slides/images/`. For a new one:

```bash
python3 commons.py "search words" "other words"              # Wikimedia Commons, prints licence
P=$(cd ../../../../api && poetry env info -p)/bin/python
$P fetchx.py "name.jpg=File:Exact Title.jpg"                 # saves + writes CREDITS.json
cd ../../../../api && PYTHONPATH=. poetry run python ../.claude/skills/make-slide-deck/scripts/up.py name.jpg
```

Only CC0 / CC BY / CC BY-SA / public-domain pictures. No identifiable patients except
from openly licensed medical images. `up.py` needs the `.jpg` extension.

## Steps, per batch of 3 decks (k, k+1, k+2)

1. **Case text**: `python3 pdfcase.py "../../../../native mock.pdf" <case#>...` → `work/cases/<n>.txt`. Read it.
2. **Write** `work/spec<k>.py` for each (rules above).
3. **Check the facts yourself, before creating.** Never call `check-facts` (the platform fact
   check): it runs on Clinical Buddy's guideline library and web search, which the user stopped
   on 2026-10-05 for cost. Instead run your own web searches (NICE CKS/NG, BNF, UKMEC, DVLA,
   BASHH) on every management claim, thresholds and doses first, and fix the spec. List what
   you checked, and anything you could not confirm, in the report.
4. **Create + rewrite**: `python3 new.py <k> <nn-slug>` (e.g. `50-amenorrhoea-...`) builds the
   deck, creates the draft and starts the rewrite (`writing_script`).
5. (`facts.py` and `decide.py` serve only decks whose platform fact check already ran.)
6. **Rewrite review**: `python3 rewritten.py <k> <k+1> <k+2>` prints every slide's narration and lint flags.
   Read all of it. Keep the asides and tags. Fix wrong facts the rewrite
   introduced (dates, "you see" on a phone call, drug advice drifting from the plan), a
   cut-down opener or conclusion, "..." and stray spaces. Write `work/e<k>.json` as
   `[[old, new], ...]` with exact substrings (curly quotes matter), then
   `python3 repl.py <k> ../../../../slide-scripts/work/e<k>.json`. Every edit must hit once; lint must be 0.
7. **Check + voice** (background, ~15 to 30 min): `bash chk.sh <k> <k+1> <k+2>`. Decks
   with `changes: 0` are voiced (asides and audio tags stay). A deck the check changed: run `rewritten.py`/`repl.py` again, then `chk.sh` again.
8. **Publish** each voiced deck: `bash pub.sh <k>`. It prints the SID and appends to
   `work/published.txt`; staging and production say `inserted`, Firestore says `created slides/<id>`.
9. **Credits**: new pictures are in `CREDITS.json` and the images folder (uncommitted, say so).

Run the waits in the background and work on the next batch meanwhile. Use zsh-safe
loops (`set -- ${=pair}`) or explicit arguments.

## Rebuilding a published deck (respin)

To give a published deck a new scenario while reusing its saved audio: keep the
diagnosis and the management lines word for word (their audio is reused), and invent
the patient, story, numbers, twist and ICE. Vary the opener (scene, quote, number,
question; never "Welcome", never the same style as the deck before).

1. Write `work/r<k>.json`: `slides` maps a slide number to `title`/`intro`/`bullets`/
   `items`/`highlights`/`img` (items must match the bullet count; highlights must be
   substrings of bullets); `presentation` merges, but a `sections` or `takeaways` list
   replaces the whole list; `edits` is `[[old, new], ...]`.
2. `python3 respin.py <k> ../../../../slide-scripts/work/r<k>.json` must print `missed 0`
   and `LINT <k>: 0 flags`. Specs apply first, then edits in order as global substring
   replaces across every slide, the title and about. Put name edits last and write the
   earlier edits with the old names. Lint flags a "Welcome" opener, "video", "..." and stray spaces; asides stay.
3. `python3 leftover.py <k> '<old names|old facts>'` to find what the edits missed.
4. Background: `bash respun.sh <k> <k+1> <k+2>` (check, restore the wanted lines, check, voice).
5. Rename `slide-scripts/<old>.json` to the new slug and update `work/d<k>.name`.
6. `bash pub.sh <k> <SID>` in the background replaces the deck in staging, production and
   Firestore (`replaced`). Run one `pub.sh` at a time.

If the queue stalls (a deck sits in one status for 20+ minutes
with nothing in the api log), restart the api's worker. Never write
`review.script.sources` or any fingerprint to skip a check.

## Report (at the end)

Per deck: number, title, SID, Firestore id. Then defaults chosen, departures from the
source case, twists added (for sign-off), fact-check decisions (accepted/dismissed and
why), `not_found` claims, new pictures with licences, and uncommitted files.
