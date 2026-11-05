# Schedule a sitting

Source: `boards/ScheduleSitting.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

[Close](Sittings.dc.html) Schedule a sitting

Steps unlock in order. Nothing is created until the last step.

[{{ s.mark }}{{ s.label }}]

Step 1 of 6

# The basics

What this sitting is, which exam it uses and when it happens.

Name
‹input: Summer finals›

Exam

‹select:
Final-year OSCE · Ready to schedule |

Year 4 mock · Ready to schedule |
›

Only exams that are ready to schedule show here. Missing one? [Set up an exam](NewExam.dc.html)

Kind

[{{ o.title }}{{ o.body }}]

Date
‹input: 26 Nov 2026›
You can leave it blank and set it later.

Year group

‹select:
Final year 2026 |

Year 4 |

None |
›

Step 2 of 6

# Pick the stations

Published stations from Final-year OSCE. Drag to set the order every candidate goes round.

{{ stationNote }}

⋮⋮{{ x.n }}{{ x.title }}{{ x.kind }}[↑] [↓] [Remove]

[Add from this exam] [Write a new station](NewStation.dc.html)

Step 3 of 6

# Who is sitting it?

Pick people one by one, or add a whole group or year group.

PeopleGroupsYear groups

‹input: Search by name or email›

Aisha Bello
aisha.bello@stmarys.ac.uk
(Signed in

Tom Hughes
tom.hughes@stmarys.ac.uk
(Signed in

Priya Nair
priya.nair@stmarys.ac.uk
(Signed in

Daniel Osei
Invited 3 Nov. Can't be scheduled until they accept.
(Not joined yet[Resend invitation]

Group: Firm B
4 trainees
(Group

7 trainees for 6 stations. In training, each trainee starts at a different station, so these must match.

7 candidates picked. Each gets their own circuit.

Step 4 of 6

# Timing and breaks

Taken from the exam. Change them for this sitting only.

Reading time
‹input: 3 min›
1 to 30

Consultation
‹input: 10 min›
1 to 180

Start time
‹input: 09:00›

Breaks

After station 2‹input: 5 min›[Remove]

After station 4‹input: 15 min›[Remove]

[Add a break] Each break is 1 to 60 minutes.

Ends about 10:41 for each candidate.

Step 5 of 6

# Who supervises?

The supervisor reviews and signs off the circuit afterwards. Any staff member can run the console on the day.

[{{ o.title }}{{ o.body }}]

Supervisor

‹select:
Dr Patel |

Dr Okafor (you) |

Ms Clarke |
›

No supervisors yet? [Invite staff](AddPeople.dc.html)

Aisha Bello
‹select:
Dr Patel |
›

Tom Hughes
‹select:
Ms Clarke |
›

Priya Nair
‹select:
Dr Patel |
›

and 4 more

Step 6 of 6

# Review and create

Check it over. You can change everything on the sitting page afterwards.

{{ formula }}

{{ formulaHelp }}

SittingSummer finals · 26 Nov 2026

ExamFinal-year OSCE

Kind{{ modeTitle }}

Year groupFinal year 2026

Timing3 + 10 min per station · breaks after 2 and 4

SupervisorDr Patel

If the sitting is made but its circuits fail, you land on the sitting with the error and a "Try again" button.

[Back]
[Continue]
[Create sitting](Sitting.dc.html)

Help

{{ help.t }}

{{ help.b }}

▸ Build spec: how to build this screen

Route
`/app/[workspace]/sittings/new`

Who sees it
manage_sittings

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/NewSitting.tsx`

- `web/src/domains/assess/SittingFields.tsx`

- `web/src/domains/assess/CircuitBuilder.tsx`

- `web/src/domains/assess/TraineePicker.tsx`

- `web/src/domains/assess/TimingFields.tsx`

API calls (all exist; add no endpoint, change no schema)

`POST /api/v1/orgs/{org_slug}/roster/resolve`Resolve Roster
Now: web/src/domains/assess/roster/api.ts

`POST /api/v1/orgs/{org_slug}/sittings`Create Sitting
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/circuits`Add Circuit
Now: web/src/domains/assess/SittingDetail.tsx, web/src/domains/assess/api.ts, web/src/foundation/routing/legacyRedirects.ts

`POST /api/v1/orgs/{org_slug}/sittings/{sitting_id}/circuits/bulk`Add Exam Circuits
Now: web/src/domains/assess/api.ts

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.
