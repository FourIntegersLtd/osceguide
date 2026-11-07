import assert from "node:assert/strict";
import { test } from "node:test";
import { PERSONAL_WORKSPACE } from "@/foundation/routing";
import type { Workspace } from "@/foundation/routing";
import { switcherGroups } from "./switcherGroups";

const org = (slug: string, kind: "institution" | "employer"): Workspace =>
  ({ kind, slug, orgSlug: slug, name: slug }) as Workspace;

test("employer workspaces sit under a Hiring heading, the rest unlabelled", () => {
  const groups = switcherGroups([PERSONAL_WORKSPACE, org("acme-health-trust", "employer"), org("st-marys", "institution")]);
  assert.deepEqual(
    groups.map((g) => [g.label, g.items.map((i) => i.slug)]),
    [
      [null, [PERSONAL_WORKSPACE.slug, "st-marys"]],
      ["Hiring", ["acme-health-trust"]],
    ],
  );
});

test("no employer workspace, no Hiring heading", () => {
  assert.deepEqual(switcherGroups([PERSONAL_WORKSPACE, org("st-marys", "institution")]).map((g) => g.label), [null]);
});
