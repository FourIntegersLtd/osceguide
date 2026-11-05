# Sittings

Source: `boards/Sittings.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. All | 2. Scheduled | 3. Running | 4. Finished | 5. Cancelled | 6. Filters | 7. Empty states

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

Run

# Sittings

A sitting is one occasion, such as the March mock. Its circuits are built for you when you schedule it.

[Schedule a sitting](ScheduleSitting.dc.html)

Next up

## March mock is running now

Final-year OSCE · Today 09:00 · 8 candidates

[Open sitting](Sitting.dc.html)

[{{ t.label }}]

Kind

‹select:
All kinds |

Formal exam |

Training |
›

Exam

‹select:
Any exam |

Final-year OSCE |

Year 3 practice |
›

From
‹input: ›

To
‹input: ›

Search
‹input: Search by sitting name›

[Clear filters]

SittingKindExamDateStatus

[

March mock

Final-year OSCE · 8 circuits · 8 candidates

Formal examFinal-year OSCEToday 09:00(Running](Sitting.dc.html) [

Year 3 practice round

2 circuits · 16 trainees

TrainingYear 3 practice12 Nov(Scheduled](Sitting.dc.html) [

Summer finals

24 circuits · 24 candidates

Formal examFinal-year OSCE26 Nov(Scheduled](Sitting.dc.html) [

Paediatrics catch-up

No circuits yet

Formal examYear 4 mockNot scheduled(Needs circuits](Sitting.dc.html)

[Load more]
What changed: the filter bar folds behind one Filters button; the list itself is today's.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/sittings`

Who sees it
Org admin and supervisors

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/Sittings.tsx`

- `web/src/domains/assess/SittingFilterBar.tsx`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/sittings`List Sittings
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

`GET /api/v1/orgs/{org_slug}/sittings/{sitting_id}`Read Sitting
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

`PUT /api/v1/orgs/{org_slug}/sittings/{sitting_id}`Update Sitting
Now: web/src/domains/assess/NewCircuit.tsx, web/src/domains/assess/NewSitting.tsx, web/src/domains/assess/SittingDetail.tsx

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 6: Filters

## Filters

‹select:
Any status |

Scheduled |

Running |

Finished |

Cancelled |
›

‹select:
Formal exam and training |

Formal exam |

Training |
›

‹select:
Any exam |

Final MB OSCE |
›
‹input: From›‹input: To›‹input: Search by name›

Every filter runs on the server. The list loads 25 at a time with Load more.

## Next up

March mock · Final MB OSCE · 12 Mar, 09:00

Covers the sittings loaded so far.

## Tab 7: Empty states

## No sittings yet

Schedule your first one.
[Schedule a sitting](ScheduleSitting.dc.html)

## Supervisor, nothing yet

An administrator schedules sittings; they will appear here.

## No sittings match.

Clear a filter to see more.

## Hire

Every "Sitting" reads "Assessment". Supervisors see no Schedule button.
