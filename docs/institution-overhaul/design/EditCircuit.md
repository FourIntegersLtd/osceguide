# Edit circuit

Source: `boards/EditCircuit.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Edit a circuit | 2. Add circuits (formal, several) | 3. Locked | 4. Candidates | 5. Stations | 6. Timing | 7. Refusals

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

[‹ Circuit](Console.dc.html)

March mock · Formal exam

# Edit circuit

Used for Edit on an existing circuit and for Add a circuit on a sitting. The Schedule wizard builds the first circuits.

[{{ t.label }}]
What changed: built from the same step parts as Schedule a sitting.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/sittings/[sittingId]/circuits/new and /circuits/[circuitId]/edit`

Who sees it
manage_sittings

Owner agent
`institution-owner` · prove with `verify-institution` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/NewCircuit.tsx`

- `web/src/domains/assess/EditCircuit.tsx`

- `web/src/domains/assess/CircuitBuilder.tsx`

API calls (all exist; add no endpoint, change no schema)

`DELETE /api/v1/orgs/{org_slug}/circuits/{circuit_id}`Delete Circuit
Now: web/src/domains/assess/CircuitBuilder.tsx, web/src/domains/assess/EditCircuit.tsx, web/src/domains/assess/SittingDetail.tsx

`GET /api/v1/orgs/{org_slug}/circuits/{circuit_id}/edit-lock`Read Edit Lock
No screen calls this today.

`PUT /api/v1/orgs/{org_slug}/circuits/{circuit_id}`Rebuild Circuit
Now: web/src/domains/assess/CircuitBuilder.tsx, web/src/domains/assess/EditCircuit.tsx, web/src/domains/assess/SittingDetail.tsx

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: Edit a circuit

## Details

Name
‹input: Circuit 3 · Chloe Imran›

Supervisor

‹select:
Ms Clarke (supervisor) |

Dr Patel (supervisor) |

Unassigned |
›

Reading (minutes)
‹input: 2›

Consultation (minutes)
‹input: 10›

## Breaks

A break goes between two stations, never after the last one. Everyone on the circuit pauses during it.

Default break length (minutes)
‹input: 5›

After station 1After station 2After station 3 · 10 minAfter station 4After station 5

## Candidates

1 of 8 selected. A formal exam circuit is one candidate's sitting: they go through every station.

Add a group

‹select:
Add a group… |

Tuesday rotation |
›

Add a year group

‹select:
Add a year group… |

Year 5 |
›

Find a candidate
‹input: Name or email›

Chloe ImranAmara OkoyeBen HartDev Shah · not signed in[Resend invitation]

## Stations (6)
At most 12 on a formal exam circuit

1.Chest pain history[↑] [↓] [✕]

2.Breaking bad news[↑] [↓] [✕]

3.Abdominal examination[↑] [↓] [✕]

4.Consent for OGD[↑] [↓] [✕]

5.Paediatric asthma[↑] [↓] [✕]

6.Prescribing review[↑] [↓] [✕]

‹input: Find a station for Final-year OSCE›

(FINALSHeadache history[Add]

(FINALSChest pain history[Added]

[Load more stations]

[Cancel](Console.dc.html) [Save changes](Sitting.dc.html)

## Tab 2: Add circuits (formal, several)

## Details

Name prefix
‹input: Exam›

Supervisor

‹select:
Ms Clarke (supervisor) |

Dr Patel (supervisor) |

Unassigned |
›

Reading (minutes)
‹input: 2›

Consultation (minutes)
‹input: 10›

## Breaks

A break goes between two stations, never after the last one. Everyone on the circuit pauses during it.

Default break length (minutes)
‹input: 5›

After station 1After station 2After station 3 · 10 minAfter station 4After station 5

## Candidates

3 of 8 selected. A formal exam circuit is one candidate's sitting: they go through every station.

Add a group

‹select:
Add a group… |

Tuesday rotation |
›

Add a year group

‹select:
Add a year group… |

Year 5 |
›

Find a candidate
‹input: Name or email›

Chloe ImranAmara OkoyeBen HartDev Shah · not signed in[Resend invitation]

## Stations (6)
At most 12 on a formal exam circuit

1.Chest pain history[↑] [↓] [✕]

2.Breaking bad news[↑] [↓] [✕]

3.Abdominal examination[↑] [↓] [✕]

4.Consent for OGD[↑] [↓] [✕]

5.Paediatric asthma[↑] [↓] [✕]

6.Prescribing review[↑] [↓] [✕]

‹input: Find a station for Final-year OSCE›

(FINALSHeadache history[Add]

(FINALSChest pain history[Added]

[Load more stations]

3 candidates make 3 circuits, one each, named Exam 1 to Exam 3.

[Cancel](Sitting.dc.html) [Create 3 circuits](Sitting.dc.html)

## Tab 3: Locked

This circuit cannot be changed right nowSomeone is taking a station right now. Changing the stations would delete that consultation.

## While the circuit is locked

Nothing on this form can be saved while the circuit is locked. While it is running, change its timings from the live circuit screen.

This circuit changed while you were editingNothing was saved. Reload to see its current state; your changes on this form will be lost. [Reload the circuit]
[Save changes · locked]
Other lock reasons: the circuit has finished; feedback has already been given on these stations.

## Tab 4: Candidates

## Candidates

‹select:
Add a group… |
›

‹select:
Add a year group… |
›
‹input: Search candidates›

Amara Okoye
Final year

[Remove]

Ben Hart (Not signed in yet
Has not accepted the invitation, so cannot be picked.

[Resend invitation]

A formal exam circuit takes one candidate: it is one person through every station.

## Tab 5: Stations

## Stations

1. Breaking bad news

[↑] [↓] [Remove]

2. Chest pain history

[↑] [↓] [Remove]

[Add stations]
Up to 12 stations. The picker loads more with Load more.

## Tab 6: Timing

## Timing

Reading (minutes)
‹input: 2›

Consultation (minutes)
‹input: 8›

Break after station 3 (minutes, 1 to 60)
‹input: 5›

Supervisor

‹select:
Dr Patel |
›

## Tab 7: Refusals

This circuit changed since you opened it. Reload to see the latest.

Administrators only

Only someone who schedules sittings can add or edit a circuit.

Station 13 cannot be added: a circuit has at most 12.

Name prefix is required when adding several circuits.
