# Station layout builder

Source: `boards/LayoutBuilder.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. New: start | 2. New: sections and fields | 3. Edit draft | 4. View a published version | 5. Loading and error states

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Administrator

[Home](Today.dc.html)

Run

[Sittings](Sittings.dc.html)
[Now running](LiveBoard.dc.html)
[Results](Results.dc.html)

Organise

[People](People.dc.html)
[Exams](Exams.dc.html)

Insight

[Reporting](Reporting.dc.html)

[Settings](Settings.dc.html)

[‹ Station templates](Exams.dc.html)

[{{ t.label }}]
Same wizard and builder as today. The marking scheme's Examiner layout uses this builder too, with the scoring field types. What changed: the name "Station template" is shown as "Station layout (optional)".

▸ Build spec: how to build this screen

Route
`/app/[workspace]/authoring/station-templates/new and /[templateId]/versions/[version]`

Who sees it
author_content

Owner agent
`content-owner` · prove with `verify-content` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/capabilities/authoring/templates/StationTemplateNewScreen.tsx`

- `web/src/capabilities/authoring/templates/StationTemplateEditScreen.tsx`

- `web/src/capabilities/authoring/templates/wizardSteps.ts`

- `web/src/capabilities/authoring/structure/`

API calls (all exist; add no endpoint, change no schema)

No calls of its own: it is a static explainer or reuses the data of the screen that links here.

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: New: start

Station layouts

# New template

Choose the exam, name the template, pick a starting layout, then save a draft. Only saved (and published) templates appear in the catalogue list.

StartExam, name, layout

Sections & fieldsThen save a draft

Exam

‹select:
Select an exam… |

*Final MB OSCE |
›

Template title
‹input: Untitled template›

Starting layouts

( ) Blank
Start from scratch · 0 sections

( ) SCA (Recommended
Patient, record, plan · 4 sections

( ) PLAB 2
Brief, patient, plan · 3 sections

( ) CASC
Brief, patient, plan · 3 sections

( ) Clinical interview
Scenario, work-up, Q&A · 4 sections

( ) Prioritisation
Trauma list and ordering · 3 sections

(•) Communication
Consent, news, conduct · 4 sections

( ) Portfolio
Brief and CV interview · 2 sections

Layouts are filtered by the chosen exam; Blank is always offered. Errors: "Please choose an exam." / "Please enter a template title."

[Cancel](Exams.dc.html) [Continue]

## Tab 2: New: sections and fields

Station layouts

# New template

Step 2 of 2: sections and fields.

Sections

⋮⋮Patient script
Patient

⋮⋮Candidate brief
Candidate brief

⋮⋮Examiner notes
Examiner

⋮⋮Faculty notes
Faculty

[+ Add section]

Candidate brief[Undo] [Redo]
‹input: Section title›‹input: Add a short description (optional)›[Section settings]

Scenario
Long text · Candidate brief · Required

Tasks
List

Results
Media

▸ + Add field

Text
Short text · Long text · List

Rich content
Media · Records · Questions and answers · Grouped list

Choices
Pick one

Scoring (feedback layouts)
Pick several · Checklist · Scale · R/A/G criterion

▸ Draft writing with AI

Exam type

‹select:
Final MB OSCE |

Custom |
›

▸ Built-in instructions for this exam (read-only)

Write a realistic station for a final-year student…

Extra notes for the AI (optional)

‹textarea: Anything you want the AI to always keep in mind for this template›

Your own main instructions

‹textarea: Replaces the usual exam instructions when exam type is Custom›

## Section

Candidate brief

Written for

( ) Patient
The script the simulated patient follows. The candidate does not see this.

(•) Candidate brief
Notes the candidate reads before starting the station.

( ) Examiner
Model answers and marking notes for the examiner after the station.

( ) Faculty
Setup, debrief and teaching notes for the people running the station. Never shown to the learner or used by the AI.

Title
‹input: Candidate brief›

Description
‹input: Shown above this section (optional)›
[Remove section]

## Field

Label
‹input: What the author fills in›

Answer format

‹select:
Long text |

Short text |

List |

Media |

Records |

Questions and answers |

Grouped list |

Pick one |
›

Used in the station as

‹select:
Candidate brief |
›

Patient sections offer: Who the patient is, Presenting complaint, Medical history, Medications, Family and social, Examination findings, Held back until asked, Acting instructions. Faculty: Faculty notes, Debrief guide.

[x] Required Authors must fill this in

Generate draft instructions

‹textarea: Tell the AI what to write in this field when someone clicks Generate draft›

Pick one / List show "Options (one per line)" or "Items (one per line)"; Records show "Columns (one per line)"; Scale shows Min and Max; scoring fields show "Feedback scoring path" (e.g. global_skills.structures_consultation).

[Back] [Cancel](Exams.dc.html) [Save draft](Exams.dc.html)

Opened from New station, this button reads "Save and publish" and returns to the station.

## Tab 3: Edit draft

Station layouts

# Communication station

Version 3. Published versions cannot be edited. Make a new draft from the list first.

Title
‹input: Communication station›

Sections

⋮⋮Patient script
Patient

⋮⋮Candidate brief
Candidate brief

⋮⋮Examiner notes
Examiner

⋮⋮Faculty notes
Faculty

[+ Add section]

Candidate brief[Undo] [Redo]
‹input: Section title›‹input: Add a short description (optional)›[Section settings]

Scenario
Long text · Candidate brief · Required

Tasks
List

Results
Media

▸ + Add field

Text
Short text · Long text · List

Rich content
Media · Records · Questions and answers · Grouped list

Choices
Pick one

Scoring (feedback layouts)
Pick several · Checklist · Scale · R/A/G criterion

▸ Draft writing with AI

Exam type

‹select:
Final MB OSCE |

Custom |
›

▸ Built-in instructions for this exam (read-only)

Write a realistic station for a final-year student…

Extra notes for the AI (optional)

‹textarea: Anything you want the AI to always keep in mind for this template›

Your own main instructions

‹textarea: Replaces the usual exam instructions when exam type is Custom›

## Section

Candidate brief

Written for

( ) Patient
The script the simulated patient follows. The candidate does not see this.

(•) Candidate brief
Notes the candidate reads before starting the station.

( ) Examiner
Model answers and marking notes for the examiner after the station.

( ) Faculty
Setup, debrief and teaching notes for the people running the station. Never shown to the learner or used by the AI.

Title
‹input: Candidate brief›

Description
‹input: Shown above this section (optional)›
[Remove section]

## Field

Label
‹input: What the author fills in›

Answer format

‹select:
Long text |

Short text |

List |

Media |

Records |

Questions and answers |

Grouped list |

Pick one |
›

Used in the station as

‹select:
Candidate brief |
›

Patient sections offer: Who the patient is, Presenting complaint, Medical history, Medications, Family and social, Examination findings, Held back until asked, Acting instructions. Faculty: Faculty notes, Debrief guide.

[x] Required Authors must fill this in

Generate draft instructions

‹textarea: Tell the AI what to write in this field when someone clicks Generate draft›

Pick one / List show "Options (one per line)" or "Items (one per line)"; Records show "Columns (one per line)"; Scale shows Min and Max; scoring fields show "Feedback scoring path" (e.g. global_skills.structures_consultation).

[Cancel](Exams.dc.html) [Save draft]

## Tab 4: View a published version

Station layouts

# History and examination

Version 2 is published, so it is read only. Make a new draft from the list to change it.

Sections

⋮⋮Patient script
Patient

⋮⋮Candidate brief
Candidate brief

⋮⋮Examiner notes
Examiner

⋮⋮Faculty notes
Faculty

[+ Add section]

Candidate brief[Undo] [Redo]
‹input: Section title›‹input: Add a short description (optional)›[Section settings]

Scenario
Long text · Candidate brief · Required

Tasks
List

Results
Media

▸ + Add field

Text
Short text · Long text · List

Rich content
Media · Records · Questions and answers · Grouped list

Choices
Pick one

Scoring (feedback layouts)
Pick several · Checklist · Scale · R/A/G criterion

▸ Draft writing with AI

Exam type

‹select:
Final MB OSCE |

Custom |
›

▸ Built-in instructions for this exam (read-only)

Write a realistic station for a final-year student…

Extra notes for the AI (optional)

‹textarea: Anything you want the AI to always keep in mind for this template›

Your own main instructions

‹textarea: Replaces the usual exam instructions when exam type is Custom›

## Section

Candidate brief

Written for

( ) Patient
The script the simulated patient follows. The candidate does not see this.

(•) Candidate brief
Notes the candidate reads before starting the station.

( ) Examiner
Model answers and marking notes for the examiner after the station.

( ) Faculty
Setup, debrief and teaching notes for the people running the station. Never shown to the learner or used by the AI.

Title
‹input: Candidate brief›

Description
‹input: Shown above this section (optional)›
[Remove section]

## Field

Label
‹input: What the author fills in›

Answer format

‹select:
Long text |

Short text |

List |

Media |

Records |

Questions and answers |

Grouped list |

Pick one |
›

Used in the station as

‹select:
Candidate brief |
›

Patient sections offer: Who the patient is, Presenting complaint, Medical history, Medications, Family and social, Examination findings, Held back until asked, Acting instructions. Faculty: Faculty notes, Debrief guide.

[x] Required Authors must fill this in

Generate draft instructions

‹textarea: Tell the AI what to write in this field when someone clicks Generate draft›

Pick one / List show "Options (one per line)" or "Items (one per line)"; Records show "Columns (one per line)"; Scale shows Min and Max; scoring fields show "Feedback scoring path" (e.g. global_skills.structures_consultation).

[Back](Exams.dc.html)

## Tab 5: Loading and error states

Loading template…

Failed to save draft. [Try again]

Template not found. It may have been removed.

Only a draft version can be edited.

Empty section
No fields yet. Add the first one below.

Empty layout
A section is written for the patient, the candidate or the examiner. Add one, then add the fields it needs.
