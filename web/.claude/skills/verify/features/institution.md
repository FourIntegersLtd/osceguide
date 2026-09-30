# Institution dashboard and sittings

## Sub-features
- Dashboard: setup checklist ("Before your first examination", n/4 done), "At a glance" counts, recent sittings.
- Sittings list and "Schedule a sitting".
- Authoring: tabs Stations, Station templates, Rubrics, Exams, Programmes.

## How to get to it (user POV)
Switch to Kings College → Overview. Sittings and Authoring are in the
institution nav.

## Driving it with playwright-core
```js
await open(run, "/app/kings/dashboard");      // h1 "Kings College"
// links: "Continue setting up", "Trainees 4", "Staff 2", "Your stations 0", "Sittings 0", "All sittings"
await open(run, "/app/kings/sittings");       // h1 "Sittings", link "Schedule a sitting", "No sittings yet"
await open(run, "/app/kings/authoring", {     // redirects to /authoring/stations
  ready: (p) => p.getByRole("tablist", { name: "Authoring section" }),
});
// tab "Stations" [selected], button "New station", combobox "Filter by exam"
```

## Gotchas
- `/app/kings/authoring` redirects to `/app/kings/authoring/stations`; before
  it settles `<main>` is empty, which looks like a broken page. Wait for the tablist.
- Counts are seed data and drift; assert the labels, and quote numbers only as
  "was N at the time".
- Scheduling a sitting writes data. Do it only in `kings`/`st-marys` and
  record it in the run log.
