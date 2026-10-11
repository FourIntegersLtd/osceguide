import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { resolveCrumb } from "@/foundation/navigation/resolveCrumb";
import { studyTabPathForSlug } from "@/capabilities/media/studyPaths";

const items = [
  { href: "/app/me", label: "Dashboard", section: null },
  { href: "/app/me/summary", label: "A to Z", section: "practice" },
  { href: "/app/me/articles", label: "Articles", section: "practice" },
];
const labels = { practice: "Practice" };
const crumb = (path: string) => resolveCrumb({ pathname: path, items, basePath: "/app/me", sectionLabels: labels, rootLabel: "Practice", deepPages: { stations: "Station" } });

describe("resolveCrumb for study detail pages", () => {
  it("puts a summary under A to Z", () => {
    assert.deepEqual(crumb("/app/me" + studyTabPathForSlug("summary", "asthma")), {
      section: "Practice",
      page: "A to Z",
    });
  });

  it("puts an article under Articles", () => {
    assert.deepEqual(crumb("/app/me" + studyTabPathForSlug("blog", "a-day-in-sca")), {
      section: "Practice",
      page: "Articles",
    });
  });

  it("still names an unlisted deep page", () => {
    assert.deepEqual(crumb("/app/me/stations/x"), { section: "Practice", page: "Station" });
  });
});
