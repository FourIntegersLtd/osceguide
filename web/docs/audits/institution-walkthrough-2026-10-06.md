# Institution walkthrough, 2026-10-06

A new institution, "Riverside Medical School", was set up from nothing on a
local stack and walked end to end in a real browser. The walk covers staff
creating the organisation, the first admin accepting the invitation, the team,
trainees, marking schemes (rubrics), exams, programmes, station templates,
stations, a one-to-one session, a group session, an exam, results, release,
and then the trainee and the supervisor signing in. Every claim below was
tried in the browser or against the API. Evidence lives in
`web/.verify/2026-10-06T*-walk-*` (screenshot, ARIA tree and run log per step;
folder names are in the appendix).

No code was changed. Nothing here has been added to `docs/BACKLOG.md`; each
breakage says whether it is already listed there.

## 1. Summary: the five things that would stop a new institution

**1. A circuit cannot be built in the app for the institution's own exam.**
After authoring and publishing two stations for its own exam, the admin opens
a sitting, presses "Add a circuit", and the Stations panel says "No stations
here yet". The builder reads the station library for the user's *consumer*
exam (`useCurrentExam`), not the sitting's programme exam. The server also
refuses the library for any organisation-authored exam: `exam_access_for`
(`api/app/features/entitlements/service_access.py:22`) checks the exam against
the platform's published codes only, so `GET /stations?exam_code=finals`
answers 403 `not_entitled` even with an entitlement row. Nothing can be run
without the API. The rest of this walk created circuits with
`POST /orgs/{slug}/sittings/{id}/circuits`, which has no such check.

**2. Trainees are invited, examined and emailed a result they cannot open.**
Rostering creates an account but no membership (BACKLOG D11). Ada was rostered,
sat two exam stations, was passed, signed off and released, and the outbox
holds "Your result is available". Signed in, she gets "Page not found" on every
organisation page, including her result. Separately, `/app` sends every new
institution user, admin and trainee alike, to the consumer exam picker ("Which
exam are you sitting? … You can change it later only by contacting support")
with no sign of their organisation.

**3. Nothing tells the admin the order things must be built in.**
The real chain is: rubric, then exam (which picks a rubric version), publish
the exam, then programme, activate it, then a station template (a custom exam
has no other layout), then stations, then a sitting, then circuits. The
Authoring tabs run in the reverse order (Stations, Templates, Rubrics, Exams,
Programmes). The dashboard checklist starts with Team and Trainees, and the
only place the chain is spelled out is the block on "Schedule a sitting",
which is reached last. Along the way a created exam vanishes from its list
(drafts are hidden by default), a draft exam can be typed into the programme
form and fails, and a station made with "No template" is a dead end with no
content form.

**4. Once a trainee is a member, they see the staff side of the organisation.**
With the membership added by hand, Ada's menu shows Programmes, Sittings,
People, Authoring and Settings. The server lets her read the whole roster
(every trainee's name, email and stations sat), every sitting and who leads
it, and every station title including drafts. Case content is not exposed.
The cause is `may_read_org` including trainees
(`api/app/features/tenancy/domain.py:108`) and the nav gating staff items on
`read_org` (`web/src/surfaces/assess/surface.ts:25`). Supervisors meanwhile
see staff buttons (Results, Add a circuit, New programme) that open to "You do
not have access to this resource".

**5. Results and review read as unfinished or contradictory.**
The admin reviewing a station is told "Automatic marking is not ready yet"
when the API actually refused it (403, the admin is not the circuit's named
supervisor), and is asked for "the mark that counts" beside a second, equally
long form. The results page counts nobody as undecided, shows "Not assessed"
for marked candidates, labels every candidate "High priority" at 100%
complete, and shows the raw code "pass". Releasing, which emails the
candidate, happens on one click with no confirmation, from one of three
release controls on the page.

## 2. The journey, step by step

Columns: what a newcomer would expect, what happened, whether the screen made
the next move obvious, and whether it worked. Evidence is the walk label; the
folder is `web/.verify/<time>-<label>`.

### Step 0. Staff create the organisation and its first admin

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Staff → Organisations | "New organisation" | Button "Provision"; dialog "Set up an organisation" | Mostly | Yes | walk-0-staff |
| After create | Taken to the new org | Toast "Next, add its first administrator." Screen stays on the list | No: find the row, open it, pick Members (tab 4 of 5) | Yes | walk-0-staff |
| Add an administrator | One admin role | Owner / Administrator / Institution administrator, default Owner, no explanation | No | Yes | walk-0b-seat |
| Invitation email | A sign-in link | Subject "You have been invited to Riverside Medical School"; copy "you never see or set it" is good | Yes | Yes (outbox) | walk-0b-seat |

### Step 1. The admin accepts and signs in

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Accept invitation | Set password, land in the org | Password form. Submitting before the page hydrates sends a GET with the password in the URL and says "That link is incomplete" | Yes | Partly | walk-1-admin |
| After accepting | Signed in | "Your account is ready. Sign in with the password you just chose." Sign in again | Yes | Yes | walk-1-admin |
| First sign-in | Riverside dashboard | ~20s blank, then `/app/me`: "Which exam are you sitting?" with consumer exams, no nav, no switcher | No | No | walk-1b-admin, walk-2-team |
| Org dashboard | A checklist in build order | "Setup · 1 of 4 done": Invite your team (marked Done with nobody invited), Add trainees, Have stations, Add a programme | Partly | Yes | walk-1b-admin |
| Navigation | Admin tasks | 17 items mixing admin, trainee and consumer study items (A to Z, Slides, Podcast, Articles, My training, Self practice) | No | Yes | walk-1b-admin |
| Settings | Organisation settings | Opens on consumer tabs (Profile, Preferences, Exam, Payments, Memory). Organisation tab: Save does nothing, logo disabled. SSO tab read-only (U-17) | No | No | walk-1b-admin |

### Step 2. The team

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Team → Add people | Invite staff by role | Clear form; roles Supervisor and Admin only | Yes | Yes | walk-2-team |
| Roles | Examiner, lead examiner | None. "Supervisors run circuits and mark them". Staff console used a third vocabulary (Owner / Administrator / Institution administrator) | No | n/a | walk-2-team |
| Invited row | Resend, history | "Invited" badge, Resend invitation, History tab | Yes | Yes | walk-2-team |

### Step 3. Trainees

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Add one person | Name, email | Full name, Email, Cohort (optional) | Yes | Yes | walk-3-trainees |
| CSV import | Names imported | A `name` column is dropped silently; rows show the literal "None" as name, group and programme | No | No | walk-3-trainees |
| Bad CSV row | "invalid email" | "No email address on line 4" for a row that had one | No | Partly | walk-3-trainees |
| Row actions | Clear choices | Edit, Resend invitation, Revoke, Delete, Anonymise, none explained | No | n/a | walk-3-trainees |
| Practice access | Part of adding | A separate "Exam access" tab | No | Yes | walk-3-trainees |
| Membership | Trainee can sign in to the org | No membership created (D11) and no warning | No | No | walk-3-trainees |

### Step 4. Content: rubrics, exams, programmes, templates, stations

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Authoring, cold | Where to start | Tabs Stations, Templates, Rubrics, Exams, Programmes: the reverse of the build order | No | n/a | walk-4-content |
| Rubric "Copy and edit" | One copy | Slow first compile; a second click made a duplicate draft rubric | No | Partly | walk-4b-rubric |
| Create exam | Exam appears | POST 201, then hidden: the list hides drafts by default | No | No | walk-4d-create |
| Rubric version picker | Latest or mine | Every historic version of every platform rubric, ungrouped | No | Yes | walk-4c-forms |
| Retire a platform exam | Not offered | Enabled; confirming gives 404 "That exam belongs to a different owner." | No | No | walk-4c-forms |
| Add programme | Pick the exam | Exam dropdown plus a free "Exam code" box; a typed draft exam fails with "That exam is draft…" | No | Partly | walk-4e-publish |
| Programmes | One place | Reachable from the nav and from Authoring, with two different intro lines | Partly | Yes | walk-4e-publish |
| Template wizard | One exam question | Asks "Exam", then "Exam type" defaulting to SCA | No | Yes | walk-4f-station |
| Platform templates | Usable or hidden | 8 platform templates shown "Not live" with "New draft" | No | n/a | walk-4f-station |
| Station with "No template" | A content form | "No layout is defined for exam finals. Import uses the B2C library shapes…" and no form | No | No | walk-4f-station |
| Station from template | Write, publish | StepRail Draft → Publish with one Publish button: works. Header keeps a disabled button labelled with its tooltip; "working on v1" after publish | Yes | Yes | walk-4f-station |
| Station library (`/stations`) | My published stations | "No stations here yet" | No | No | walk-4f-station |

### Step 5. A session, a group session and an exam

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Schedule a sitting, no programme | A pointer | Clear block linking to Programmes | Yes | Yes | walk-5a-sitting |
| Schedule a sitting | Session vs exam | Training: "Each trainee is paired with one station, and they rotate". Exam: "One candidate takes every station…" plus breaks. Clear | Yes | Yes | walk-5a-sitting |
| Sitting header | One status | "Not scheduled" beside "Scheduled" (later beside "Completed") | No | Yes | walk-5b-circuit |
| Add a circuit | Pick stations | "No stations here yet" for two published org stations (summary item 1) | No | **No** | walk-5c-builder, walk-5d-circuits |
| Lead and trainee pickers | Names | Emails only for staff and for CSV trainees | Partly | Yes | walk-5c-builder |
| Circuit runner | Run it | 4-step strip (Start, On station, Reading time, Consultation), server clock, Pause, Extend, Reset, Resend patient, End with a reason, Listen in. Header "Supervisor:" with no name | Yes | Yes (no voice locally) | walk-5e-run |
| Now running | Live board | "Nothing is running. Circuits appear here the moment a supervisor starts one." plus an "Earlier" list | Yes | Yes | walk-6c-review |

### Step 6. Results, review, decision, release (exam sitting)

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Results | Who is waiting on me | "4 of 4 stations marked · 0 of 2 released"; Outcomes Passed 0 Failed 0 Inconclusive 0 Awaiting marking 0 with 2 undecided; Score "Not assessed" | No | Partly | walk-6a-results |
| Review order | Who to look at first | Both candidates "High priority" at "100% complete" | No | n/a | walk-6a-results |
| Mark this station | Machine marks, then mine | Two full forms ("Your marking", "The lead's review"), two Save draft buttons; "Automatic marking is not ready yet" (really a 403) | No | Partly | walk-6c-review, walk-6d-release |
| Complete review, nothing rated | Told what's missing | "Still to rate before completing: Global skills, Tasks, Relating to others." Clear | Yes | Yes | walk-6c-review |
| The decision | Pass, reason, sign off | Pass/Fail/Inconclusive/Withheld with one-line meanings; rationale required; "Before this can be signed off" checklist; recruitment outcome "The candidate does not see it". Good | Yes | Yes | walk-6c-review |
| Sign off | Needs reviews done? | Allowed with both stations "Awaiting review" (BACKLOG R-2) | Partly | Yes | walk-6c-review |
| Back to draft | Confirm | "Back to draft?" dialog, clear | Yes | Yes | walk-6c-review |
| Release | Confirm, email | "Release all 1", "Release to the candidate" and a "Candidates to release" checklist; "Release all 1" releases at once and queues "Your result is available" | Partly | Yes | walk-6d-release |
| Outcome cell | "Pass" | "pass" | n/a | Yes | walk-6d-release |
| Exports | CSV, PDF | Download CSV, Export readout, Result PDF after release | Yes | Present | walk-6d-release |
| Training sitting results | Formative view | Same Outcome/decision columns and Pass/Fail counts | No | Yes | walk-6d-release |

### Step 7. The trainee (Ada)

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Accept invitation | Signed in | Same "Sign in with the password you just chose" bounce | Yes | Yes | walk-7a-trainee |
| `/app` | Their training | Consumer exam picker, before and after membership | No | No | walk-7a-trainee |
| Any org page, no membership | My result | "Page not found … belongs to a workspace you are not in." | No | **No** (D11) | walk-7a-trainee (first) |
| My training, with membership | Sittings | "Hello, Ada." sittings with status; sitting detail with "Before you start" and "Review station". Good | Yes | Yes | walk-7a-trainee (second) |
| Result, with membership | Outcome | "Released 06/10/2026", Pass, rationale, Download PDF, "I have read this". Good | Yes | Yes | walk-7a-trainee (second) |
| Self practice | Org stations | 2 published stations, "1 more is a draft". Opening one creates an attempt at once; "There is no written brief for this station." | Yes | Yes | walk-8-sup |
| Staff pages as trainee | Not shown | Full staff nav; roster, sittings and authoring lists readable; Team shows an error and "No staff yet"; Now running loops on 403 | No | Leaks | walk-7c-trainee-staff |

### Step 8. The supervisor

| Screen | Expected | Saw | Knew next? | Worked? | Evidence |
|---|---|---|---|---|---|
| Dashboard | My circuits | "Nothing is assigned to you" while the sitting marks both circuits "Your circuit" (they had ended) | No | Partly | walk-8-sup |
| Sitting | Run or mark | Edit, Add a circuit, Results shown; Results opens to "You do not have access to this resource / Try again" | No | No | walk-8-sup |
| Slot review | Mark | Sees the automatic marking (the admin could not); the lead's section shows the raw access error | Partly | Yes | walk-8-sup |
| Runner, ended | Mark stations | "This circuit has ended. Its stations can still be marked…" with Mark links. Good | Yes | Yes | walk-8-sup |

## 3. Breakages, ranked

"New" means not in `docs/BACKLOG.md` as of today.

| # | Severity | What breaks | Where | Backlog |
|---|---|---|---|---|
| B1 | Critical | Circuit builder lists no stations for an org-authored exam; no circuit can be made in the UI | `domains/assess/CircuitBuilder.tsx` (library scoped by `useCurrentExam`); `api/app/features/entitlements/service_access.py:22` (`exam_access_for` ignores org exams) | New |
| B2 | Critical | Rostered trainees get no membership; their portal and released result are "Page not found" | `POST /orgs/{slug}/trainees` | Already listed (D11 / B57) |
| B3 | High | `/app` lands institution admins and trainees on the consumer exam picker, which warns the choice is permanent | `web/src/app/app/page.tsx`, consumer exam gate | New |
| B4 | High | Trainee members can read the full roster (names, emails), all sittings and authoring lists, and see staff navigation and buttons | `api/app/features/tenancy/domain.py:108`; `web/src/surfaces/assess/surface.ts:25` | New |
| B5 | High | A newly created exam disappears: the list hides drafts by default | `capabilities/authoring/sections/ExamsSection.tsx:41-49` | New |
| B6 | High | "No template" station for a custom exam saves but has no content form | station detail, "No layout is defined for exam…" | New |
| B7 | Medium | Slot review reports a 403 as "Automatic marking is not ready yet"; admins never see machine marks unless named supervisor | `domains/assess/SlotReview.tsx:56`; `api/app/features/attempts/service_access.py:41-51` | New |
| B8 | Medium | Accept-invitation (and login) submitted before hydration puts the password in the URL | `capabilities/account/ResetPassword.tsx` | New |
| B9 | Medium | CSV import silently drops a `name` column; rows show "None" | trainee CSV importer | New |
| B10 | Medium | Retire enabled on platform exams, fails with 404 | `ExamsSection.tsx:150-153` | New |
| B11 | Medium | Programme form's free "Exam code" box accepts a draft exam, which then fails | programme dialog | New |
| B12 | Medium | Station library (`/stations`) shows none of the org's published stations | `capabilities/stations` library | New (same root as B1) |
| B13 | Medium | Release emails the candidate on one click with no confirmation | `domains/assess/results/Results.tsx` release bar | New |
| B14 | Medium | Failures rendered as empty: Team shows the access error and "No staff yet / Invite a supervisor"; Now running retries a 403 stream | Team screen; live board | New |
| B15 | Low | Supervisor sees Results, Add a circuit, Edit, New programme that 403 | assess nav and sitting actions | New |
| B16 | Low | Settings → Organisation Save does nothing; SSO read-only | settings tabs | Already listed (U-17) |
| B17 | Low | Duplicate rubric from a double click on "Copy and edit" | rubric copy | New |
| B18 | Low | Runner header "Supervisor:" with an empty name | `domains/assess/sessions/CircuitRunner.tsx:89` | New |
| B19 | Low | Outcome cell shows the raw code "pass" | `domains/assess/results` candidate table | New |
| B20 | Low | Result email payload carries only `sitting_id` | `candidate_result_released` template | New |

Not a breakage: a decision request returned 500 once. The web proxy logged
`ECONNRESET` while the local API reloaded; a direct call returned 200. The
alert's advice about ports is development-only (`foundation/platform-client/client.ts:98`).

## 4. Confusions (worked, but a newcomer would not understand)

Ranked by how likely they are to stop someone.

1. **No build order.** Dashboard checklist (`domains/assess/dashboard/support.ts:21`) runs Team, Trainees, Stations, Programme, and marks "Invite your team" done when only the admin exists. Authoring tab order is the reverse of the chain.
2. **Navigation of 17 items** mixing admin, trainee and consumer study items; "People" and "Team" side by side (`surfaces/assess/surface.ts`).
3. **Two forms on "Mark this station"**, each about 30 G/A/R rows, labels like "Listens curiosity" and "Rules in out disease" (`domains/assess/SlotReview.tsx`, `results/GpLeadReview.tsx`).
4. **Results numbers that don't add up:** undecided candidates counted nowhere, "Not assessed" next to "2 of 2 stations marked", "Not started" meaning "not decided", everyone "High priority" (`results/Results.tsx`, `results/CohortRanking.tsx`). The score column may be affected by the local fixture and should be confirmed on staging.
5. **Three release controls** after one sign-off (`results/Results.tsx`, `results/CandidateDecision.tsx`).
6. **Sign-off without reviews.** Allowed while stations say "Awaiting review", and nothing says whether that is fine (BACKLOG R-2).
7. **Roles.** Staff console: Owner, Administrator, Institution administrator. Organisation: Supervisor, Admin. Results: "the lead's review". No examiner role.
8. **Two exam questions in the template wizard** ("Exam", then "Exam type" defaulting to SCA) (`capabilities/authoring/templates`).
9. **Platform templates shown "Not live" with "New draft"** to an org admin.
10. **Rubric version picker** lists every historic version, ungrouped.
11. **Programmes in two places** with different intro text.
12. **Sitting header** shows "Not scheduled" and a status badge together (`domains/assess/SittingDetail.tsx`).
13. **Supervisor dashboard** says nothing was ever assigned once circuits end.
14. **Roster row actions** Revoke, Delete and Anonymise unexplained; practice access lives on a separate tab.
15. **Staff "Provision"** and no jump to the new organisation after creating it.
16. **Accept then sign in again** for every invited person.
17. **Self practice opens an attempt** as soon as a station is opened, and a template-made station had no brief with no warning while authoring.

What worked well and should be kept: the "Schedule a sitting" block when no
programme exists, the training vs exam wording, the circuit runner's strip and
controls, the decision panel's outcome meanings and sign-off checklist, the
"Back to draft?" dialog, the trainee's sitting, result and self-practice
screens once they have a membership, and the station StepRail.

## 5. Where the StepRail and NextStepBar pattern fits

The pattern from staff media and stations: a pure `.ts` helper returns
`RailStep[]` (`todo` / `attention` / `done`, each with a note) and one
`NextAction` (`line` plus the single primary action), and the screen renders
`NextStepBar` above `StepRail` (`foundation/ui/StepRail.tsx`;
`capabilities/staff-media/content/steps.ts`). Results already has a related
helper, `domains/assess/results/candidateNeighbours.ts`, and the template wizard has
its own `PlatformTemplateWizardStepStrip.tsx`.

| Flow | Use it? | Proposed steps | Helper | Replaces |
|---|---|---|---|---|
| Organisation setup | **Yes, first** | Marking scheme → Exam → Programme → Station template → Stations → Team → Trainees → First sitting | Extend `dashboard/support.ts` `setupSteps` (it already says "in the order they have to happen"); the API `OrgSetup` needs flags for rubric, exam, template | The four-tile checklist; fixes confusion 1 and the "Invite your team" false tick |
| Sitting lifecycle | **Yes** | Schedule → Circuits → Run → Mark → Decide → Release | New `domains/assess/sittingSteps.ts` from sitting status, circuit states and the report counts | The status badge plus "Not scheduled" header, the three release controls (one NextStepBar action: "Release 1 signed-off result"), and the Outcomes counts (add "Undecided") |
| Candidate result | **Yes, extend** | Marked → Reviewed → Decided → Signed off → Released | Fold into `results/candidateNeighbours.ts` | The Status column words ("Not started"), and makes "sign off before review" visible as an `attention` step |
| Station review page | Partly | Automatic marking → Your marks → Lead's mark | Small helper in `results/reviewForm.ts` | Two stacked forms; shows which form is this person's to fill, and says plainly when automatic marking is withheld |
| Rubric | Yes | Draft → Preview → Trial → Publish → Used by an exam | `capabilities/authoring/rubrics` | The builder's tabs as the only progress cue; stops the duplicate copy by making "Copy" a step, not a button |
| Exam | Yes | Pick rubric → Draft → Publish → Programme | `capabilities/authoring/sections/ExamsSection.tsx` helper | The disappearing draft (the rail keeps it in view) |
| Station template and station | Keep, align | Template: Exam → Layout → Fields → Publish. Station: Template → Draft → Publish (already 2 steps) | Reuse `RailStep` in the wizard instead of `PlatformTemplateWizardStepStrip` | Two strip styles; drop the disabled header button whose label is its tooltip |
| Trainee onboarding | Yes, as a row status | Added → Invited → Accepted → Member → Practice access → Booked | `domains/assess` roster helper | "Invited" badge alone; would have exposed D11 to the admin |
| Accept invitation | Small | Set password → Signed in → In your organisation | `capabilities/account/ResetPassword.tsx` | The bounce to sign-in and the consumer exam picker |
| Circuit runner | Already has it | Start → On station → Reading → Consultation | Keep; the model the others should look like | n/a |

Order of value: organisation setup, sitting lifecycle, candidate result, then
the rest.

## 6. Vocabulary and navigation

- **Session words.** People say session, group session and exam. The product
  says sitting, circuit, programme and slot. A training sitting with a
  one-trainee circuit is "a session"; several trainees is "a group session";
  an exam-mode sitting is "an exam". Put that mapping on "Schedule a sitting".
- **Feedback template is "Rubric".** Call it "Marking scheme" everywhere (the
  programme hint already does: "its exam needs a published marking scheme").
- **One roles vocabulary** across staff console, Team and results, with an
  examiner or lead role if "the lead's review" is a real person.
- **Navigation for an admin:** Overview, Sittings, Now running, People (trainees
  and staff as tabs), Build (marking schemes, exams, programmes, templates,
  stations, in build order), Settings. Move My training, Self practice and the
  study library to trainees.
- **Navigation for a trainee:** My training, Self practice, Study, Community,
  Settings. No staff items.
- **Settings for an admin** opens on Organisation, not the consumer Profile.
- **One Programmes entry**, inside Build.

## 7. Not tested locally

| What | Why | How to test on staging |
|---|---|---|
| The live consultation (patient, reading time, clocks running out) | No LiveKit locally; the runner logged "LiveKit credentials are not configured" | `verify-attempt-engine` deployed level: one training circuit and one exam circuit with a real trainee account |
| Automatic marking of a real attempt | Marked work was faked with a fixture (`assessment_results` with framework `sca` on a custom exam) | Run one exam circuit on staging and check the Score column and Review order (confusion 4) |
| Email delivery | No mail key locally; invitations show `failed` and the release email `pending` in the outbox | Send one invitation and one release on staging; check the links and that failed delivery shows on Team or People |
| SSO | Org SSO tab is read-only and needs an identity provider | Staff-console SSO form against a test Entra tenant |
| Supervisor and trainee write buttons | Not pressed, to avoid creating more data | Press each as a supervisor and a trainee on staging; record 403s and copy |

## Appendix

**Organisation:** `riverside-1791303298`, "Riverside Medical School", left in the
local database.

**Accounts** (all `@example.com`, password `Riverside-walk-2026!`):
`riverside.admin.1791303298`, `riverside.sup.1791303298`,
`riverside.t1.1791303298` (Ada Lovelace) to `riverside.t5.1791303298`.

**Local database changes made for the walk:**

- Circuits were created through the API (B1 blocks the UI): "Ada one-to-one"
  and "Afternoon group" in the training sitting "Tuesday practice session",
  "Finals circuit A" and "Finals circuit B" in the exam sitting "Finals mock
  exam".
- A fixture marked the exam slots and the group circuit's slots: `exam_slot`
  attempts with `room_name='walk-fixture'` and `assessment_results` with
  `policy_version='walk-fixture'`. It was torn down at the end.
- A `trainee` membership was inserted for Ada to simulate the D11 fix. It is
  left in place.
- A decision for Ada was signed off and released (Pass).
- Opening a self-practice station as Ada created one practice attempt, which is left in place.

**Evidence folders** (`web/.verify/`): `walk-0-staff`, `walk-0b-seat`,
`walk-1-admin`, `walk-1b-admin`, `walk-2-team`, `walk-3-trainees`,
`walk-4-content`, `walk-4b-rubric`, `walk-4c-forms`, `walk-4d-create`,
`walk-4e-publish`, `walk-4f-station`, `walk-5a-sitting`, `walk-5b-circuit`,
`walk-5c-builder`, `walk-5d-circuits`, `walk-5e-run`, `walk-6a-results`,
`walk-6b-decide`, `walk-6c-review`, `walk-6d-release`, `walk-7a-trainee` (two
runs: without and with membership), `walk-7c-trainee-staff`, `walk-8-sup`. Each
is prefixed with its ISO time. The driving scripts were deleted after the walk.
