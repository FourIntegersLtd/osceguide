# App shell: Help, search, nav icons

## Sub-features
- Toolbar (md and up): breadcrumb, Search pill (⌘K), and a "Help" button with Athena's face. A Notifications bell link sits beside Search with the unread badge (none on the sidebar item); `/app/me/inbox` redirects to `/app/me/notifications`. On Contact, Notifications, Settings and Community the dock titled "Help" has no "Talk to Athena" button; on /mocks it does.
- Phones have no toolbar; the floating "Help" button (also Athena's face) is the only one. It stays on every route, before and after the dock loads.
- Help opens the dock through the `osce:open-athena` event.
- Search: type 2+ characters; after 250ms it lists Stations (Train only) and Help articles, then "Ask Athena about “<q>”" ("Help with “<q>”" on Contact, Notifications, Settings, Community). Pages (nav items) match instantly. A failed group says "Some results could not load".
- Nav icons are all Lucide (`react-icons/lu`): Dashboard LayoutDashboard, AI Practice Mic, Notifications Bell, Marketplace Store, Community Users, collapse PanelLeftClose/Open.

## Driving it with playwright-core
```js
await p.setViewportSize({ width: 1400, height: 900 });       // 390 wide for the floating button
await open(run, "/app/me/dashboard");
p.getByRole("button", { name: "Help", exact: true }).locator("visible=true")   // toolbar and FAB both exist in the DOM; one is display:none
await p.getByRole("button", { name: /^Search/ }).first().click();
await p.getByRole("textbox", { name: /Search stations/ }).fill("asthma");
await p.getByRole("option").allInnerTexts();                  // "Stations\n\n<title>", "Athena\n\nAsk Athena about …"
await p.getByRole("button", { name: "Collapse sidebar" }).click();
```

## Gotchas
- The dock only loads after Help is opened once; a gate that differs between the placeholder and the dock shows up only after that, so open Athena, close her, then look again (and navigate client-side, because `open()` reloads and resets the dock).
- A local library may have no station titled for your query: rename a throwaway fixture station in the local database to test, and put it back.
- Opening Help locally ends in "The voice service is not available" and 503s on `voice-token`: no LiveKit, expected.
- The cookie dialog and the walkthrough scrim swallow clicks: close them first ("Close dialog", "Continue without analytics").
- Phone layout (390x844, `hasTouch`, `isMobile`): scroll with `mouse.wheel` from the middle of the screen, then check the last content with `toBeInViewport`. It is an IntersectionObserver, so a box clipped by an ancestor counts as off screen; `scrollTop` and `getBoundingClientRect` do not. Add init scripts for `localStorage.installPromptDismissed=true` and `sessionStorage.exam_date_prompt_skipped=1`, or a modal holds the scroll. `e2e/support/phone.ts` has the helpers.
- For a peer room's layout, insert the session rather than pairing two people: `seedPeerSession` in `e2e/support/db.ts`, with phase `preparation` or `consultation`. A free account can create only 3 mock sessions, and walkthrough accounts run out, so use a fresh e2e account for the station room.
