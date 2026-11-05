# How to build from these boards

Source: `boards/BuildGuide.dc.html`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`.

## Always on screen (menu, header, notes, build spec)

## How to build from these boards

Written for the developer, human or model, who turns a board into code. Read this once, then open any board's "Build spec" at the bottom.

- Boards run left to right in the order a new admin meets them. Build in the phase order of the plan: navigation and Home first, then Exams, Sittings, People, Results, Invoices.

- The api already does everything. Every call a board needs is listed in its Build spec, with today's file that makes it. Reuse that function. If a board seems to need data the list does not have, stop and ask: do not add an endpoint.

- Tabs = states. Each tab across the top of a board is a screen or a state of one (empty, error, read only, busy). Build all of them.

- Boxes = dialogs. A button that opens a box on the board opens a `Modal` in the app. A yes/no box is a `ConfirmModal` with the same red button.

- Words are the spec. Copy them exactly. A sentence on a board is either today's app copy or a deliberate change named in the board's "What changed" note.

- Components. Use `foundation/ui` only: `B2CHero`, `B2CSegmentedTabs`, `B2CGroupedSection`, `QuietCard`, `StepGuide`, `EmptyState`, `Modal`, `ConfirmModal`. No new colours or type sizes; tokens from `foundation/ui/tokens.css`.

- One primary button per screen. A disabled button always shows why, in words under it.

- Done means seen working. Run the owner's verify skill and the web `verify` skill against a seeded org (`node scripts/seed-demo-org.mjs`), as admin, supervisor, trainee and hire admin.
