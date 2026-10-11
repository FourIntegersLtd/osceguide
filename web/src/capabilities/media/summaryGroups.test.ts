import assert from "node:assert/strict";
import { test } from "node:test";
import type { MediaItem } from "@/capabilities/media/api";
import { jumpLinks, summaryGroups } from "@/capabilities/media/summaryGroups";

function item(title: string, specialties: string[]): MediaItem {
  return { id: title, title, content: { specialties } } as unknown as MediaItem;
}

const items = [item("Asthma", ["Respiratory"]), item("Angina", ["Cardiology"]), item("COPD", ["Respiratory", "Cardiology"])];

test("the specialty view jumps to each specialty, the A to Z view to each letter", () => {
  assert.deepEqual(jumpLinks(summaryGroups(items, "specialty")), [
    { key: "Cardiology", href: "#summary-Cardiology" },
    { key: "Respiratory", href: "#summary-Respiratory" },
  ]);
  assert.deepEqual(jumpLinks(summaryGroups(items, "az")).map((link) => link.href), ["#summary-A", "#summary-C"]);
});

test("an item with two specialties is listed under both; one group needs no jump row", () => {
  const groups = summaryGroups(items, "specialty");
  assert.deepEqual(groups.Cardiology?.map((entry) => entry.title), ["Angina", "COPD"]);
  assert.deepEqual(jumpLinks(summaryGroups([item("Asthma", ["Respiratory"])], "specialty")), []);
});
