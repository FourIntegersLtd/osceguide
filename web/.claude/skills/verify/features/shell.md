# App shell: Help, search, nav icons

## Sub-features
- Toolbar (md and up): breadcrumb, Search pill (⌘K), and a "Help" button with Athena's face. No Inbox icon: the unread count is a badge on the sidebar Inbox item (a dot when the rail is collapsed).
- Phones have no toolbar; the floating "Help" button (also Athena's face) is the only one. It stays on every route, before and after the dock loads.
- Help opens the dock through the `osce:open-athena` event.
- Search: type 2+ characters; after 250ms it lists Stations (Train only) and Help articles, then "Ask Athena about “<q>”". Pages (nav items) match instantly. A failed group says "Some results could not load".
- Nav icons are all Lucide (`react-icons/lu`): Dashboard LayoutDashboard, AI Practice Mic, Inbox Mail, Marketplace Store, Community Users, collapse PanelLeftClose/Open.

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
