# Partner dashboard

Source: `boards/Partner.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. Overview | 2. Performance | 3. Your fee | 4. How we count | 5. Reporting | 6. Team | 7. Custom dates and errors

## Always on screen (menu, header, notes, build spec)

SM

St Mary's Medical School

Partner admin

[Dashboard](Partner.dc.html)
[Reporting](Partner.dc.html)
[Team](Partner.dc.html)

Partner

# Northern Deanery dashboard

See how people from your links are using OSCE Guide. All dates are UK calendar days.

[{{ t.label }}]
Partner arm unchanged. Its nav is Overview, Reporting and Team.

▸ Build spec: how to build this screen

Route
`/app/[workspace] (partner surface)`

Who sees it
Partner admin and reporters

Owner agent
`access-owner` · prove with `verify-access` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/partner/Dashboard.tsx`

- `web/src/domains/partner/Reporting.tsx`

- `web/src/domains/partner/api.ts`

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

## Tab 1: Overview

‹select:
This month |

Last month |

Last 30 days |

Last 3 months |

Last 6 months |

Custom |
›

‹select:
All exams |

SCA |

PLAB |

ORTHO |
›
All exams · 1 Nov 2026 – 5 Nov 2026 · UK calendar days[Reset filters] Updated 14:02

Fee estimates are a guide only The fee shown here is an estimate from our arrival counts. You invoice from your own click records; nothing on this page is a bill.

Overview

## How your links are performing

Visits, sign-ups, and your estimated fee for this period.

Link visits

1,240

How many times someone opened a page with your link. 980 unique people.

Sign-ups

86

New accounts where we recorded you as the source they came from.

Estimated fee

£496

A rough guide: your link visits in this period times our agreed rate per visit. You invoice from your own records.

## From visit to payment

How many people reached each step

Visited

1,240

100% of visits

Signed up

86

6.9% of visits

Paid

21

1.7% of visits

## Tab 2: Performance

‹select:
This month |

Last month |

Last 30 days |

Last 3 months |

Last 6 months |

Custom |
›

‹select:
All exams |

SCA |

PLAB |

ORTHO |
›
All exams · 1 Nov 2026 – 5 Nov 2026 · UK calendar days[Reset filters] Updated 14:02

## Link visits over time

How many times people opened your links

## Sign-ups over time

New accounts from your links

## By exam

How link visits split across SCA, PLAB, and Ortho.

SCA 62% of visits

PLAB 30% of visits

Ortho 8% of visits

## Tab 3: Your fee

‹select:
This month |

Last month |

Last 30 days |

Last 3 months |

Last 6 months |

Custom |
›

‹select:
All exams |

SCA |

PLAB |

ORTHO |
›
All exams · 1 Nov 2026 – 5 Nov 2026 · UK calendar days[Reset filters] Updated 14:02

Fee estimates are a guide only The fee shown here is an estimate from our arrival counts. You invoice from your own click records; nothing on this page is a bill.

## Estimated fee over time

Weekly estimated fee from your link visits

## Tab 4: How we count

## How we count your results

These are the rules behind the numbers you see here. If something looks wrong, tell us the dates you were viewing and what seemed off.

What the numbers mean

Link visit (Plain English
Someone clicked your link and opened a page on OSCE Guide.

Unique people (Plain English
How many different people visited. The same person can open your link more than once.

Sign-up (Plain English
Someone created an OSCE Guide account after coming from your link.

Paid (Plain English
Someone who signed up through your link and paid for a subscription in the dates you selected.

Estimated fee (Plain English
Link visits in the date range times our agreed rate per visit (pilot default £0.40). This is a guide only. You invoice from your own click records.

How we decide who gets credit

Which link gets credit (Plain English
We credit the first partner link someone clicks. If they are already linked to a partner, a later link will not replace it.

How long we remember a visit (Plain English
A sign-up can be linked to your visit for up to 90 days after they clicked.

Date range (Plain English
Visits and your estimated fee use when people clicked. Sign-ups use when they registered. Paid uses when they subscribed.

Filters (Plain English
Choosing an exam or campaign updates every number on the dashboard to match.

## Tab 5: Reporting

Partner

# Reporting

Your tracking references, and who can see the numbers.

## Tracking references

ndeanery-sca-spring
SCA · /sca

ndeanery-newsletter
PLAB · /plab

Empty: "No references yet. A reference appears here the first time somebody arrives through one of your links."

## Who can read this

A reporter sees these numbers and nothing else. Ask OSCE Guide staff to add someone. Reporters are added by us, not by your team.

## Tab 6: Team

Partner

# Team

Who can run circuits and sign off results in this organisation.

The same Members / Add people / History screens as the People › Staff tab, shown with "Team" as the title. Only with manage_team.
[See the Staff tab](People.dc.html)

## Tab 7: Custom dates and errors

## Custom date range

Choose the start and end dates for this report.

From
‹input: ›

To
‹input: ›

The start date must be on or before the end date.

We couldn't load these numbers Network error. Nothing here is zero; it just hasn't loaded. [Try again]

No activity yet
When people open your links, the numbers will show up here.

Nothing to show for these dates
Try widening the date range or removing filters.
