# Invoices

Source: `boards/Invoices.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

Tabs: 1. All invoices | 2. One invoice

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

[‹ Settings](Settings.dc.html)

Settings

# Invoices

Raised by OSCE Guide for St Mary's Medical School.

Money: needs your reviewA new screen on existing routes (GET /orgs/{slug}/invoices, GET one, PUT po-number). Built only after your sign-off and a security review.

[{{ t.label }}]
Org admins only (the routes use OrgAdmin). Raising and editing invoices stays in the staff console. Owner: access-owner.

▸ Build spec: how to build this screen

Route
`/app/[workspace]/settings (Invoices tab, NEW)`

Who sees it
Org admin. Money: the user reviews it, plus /security-review

Owner agent
`access-owner` · prove with `verify-access` then the web `verify` skill

Design
`web/docs/DESIGN.md`, assess skin, `foundation/ui` only

Files to change or reuse

- `web/src/domains/assess/settings/ (new InvoicesPanel.tsx)`

API calls (all exist; add no endpoint, change no schema)

`GET /api/v1/orgs/{org_slug}/invoices`List Invoices
No screen calls this today.

`GET /api/v1/orgs/{org_slug}/invoices/{invoice_id}`Read Invoice
No screen calls this today.

`PUT /api/v1/orgs/{org_slug}/invoices/{invoice_id}/po-number`Set Invoice Po Number
No screen calls this today.

Steps

- Each tab on this board is one screen or state. Build every one; none is optional.

- Each button that opens a box is a `Modal` (or `ConfirmModal` for a yes/no). Open each box on this board to see its words.

- Copy every word on the board exactly, including the empty, error and busy texts. Put nouns through `useAssessWords` so hire reads its own words.

- Find the button's call in the list above, by its summary. Today's caller (the "Now:" file) already makes that call: reuse its function from that file's `api.ts`. Do not write a new fetch.

- Show a write button only to the person in "Who sees it". Anyone else gets the same screen with no write buttons.

- Write a failing test first (Testing Library, assert the literal words), then build, then run `npm run ci`.

- Live data comes from the existing SSE streams (`useMeEvents` or the `*/stream` route above). Never poll.

- Nothing that exists today may disappear. If a control on today's screen is not on this board, stop and ask.

## Tab 1: All invoices

InvoiceIssuedDueTotalStatusPO number

INV-2026-01421 Nov 20261 Dec 2026£4,800.00(IssuedPO-88231[Open]

INV-2026-00981 Aug 202631 Aug 2026£4,800.00(PaidPO-77410[Open]

INV-2026-00511 May 202631 May 2026£1,200.00(VoidNot set[Open]

[Load more]

Empty: "No invoices yet. Invoices OSCE Guide raises for your organisation appear here."

## Tab 2: One invoice

## INV-2026-0142

St Mary's Medical School · issued 1 Nov 2026 · due 1 Dec 2026

(Issued

LineQtyAmount

Institution plan, Nov 2026 to Jan 20271£4,000.00

VAT 20%£800.00

Total£4,800.00

Purchase order number

‹input: PO-88231›[Save PO number]

Your finance team's reference. It can change until the invoice is paid or void.

Notes from OSCE Guide: Termly billing.
[Back to invoices]
