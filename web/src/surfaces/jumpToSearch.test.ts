import assert from "node:assert/strict";
import { test } from "node:test";
import { NO_REMOTE, searchJumpTo } from "./jumpToSearch";

type Deps = NonNullable<Parameters<typeof searchJumpTo>[3]>;

const station = { id: "s1", title: "Asthma review" };
const article = { slug: "how-asthma", title: "Asthma stations" };

function deps(over: Partial<{ stations: unknown; articles: unknown }> = {}) {
  const calls: { stations: unknown[]; articles: unknown[] } = { stations: [], articles: [] };
  const fake = {
    browseLibrary: async (params: unknown) => {
      calls.stations.push(params);
      if (over.stations instanceof Error) throw over.stations;
      return { items: [station] };
    },
    fetchHelpArticles: async (...args: unknown[]) => {
      calls.articles.push(args);
      if (over.articles instanceof Error) throw over.articles;
      return [article];
    },
  } as unknown as Deps;
  return { fake, calls };
}

test("a short query asks nothing", async () => {
  const { fake, calls } = deps();
  assert.deepEqual(await searchJumpTo(" a ", { examCode: "sca", stations: true }, undefined, fake), NO_REMOTE);
  assert.equal(calls.stations.length + calls.articles.length, 0);
});

test("a consumer query finds stations and help, with the group limit asked for", async () => {
  const { fake, calls } = deps();
  const found = await searchJumpTo("asthma", { examCode: "sca", stations: true }, undefined, fake);
  assert.deepEqual(found.stations, [station]);
  assert.deepEqual(found.articles, [article]);
  assert.equal(found.failed, false);
  assert.deepEqual(calls.stations[0], { examCode: "sca", search: "asthma", limit: 5 });
  assert.deepEqual(calls.articles[0], ["sca", undefined, "asthma"]);
});

test("an arm without the consumer library never asks for stations", async () => {
  const { fake, calls } = deps();
  const found = await searchJumpTo("asthma", { examCode: null, stations: false }, undefined, fake);
  assert.deepEqual(found.stations, []);
  assert.equal(calls.stations.length, 0);
  assert.equal(found.articles.length, 1);
});

test("one group failing is said, and the other still shows", async () => {
  const { fake } = deps({ stations: new Error("down") });
  const found = await searchJumpTo("asthma", { examCode: "sca", stations: true }, undefined, fake);
  assert.deepEqual(found.stations, []);
  assert.equal(found.articles.length, 1);
  assert.equal(found.failed, true);
});
