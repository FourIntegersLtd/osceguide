import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { livePricedPlans } from "@/domains/marketing/support/livePlans";

const card = (name: string, price: number) => ({ name, price });

describe("livePricedPlans", () => {
  const cards = {
    trial: card("Free Trial", 0),
    monthly: card("1 Month", 24.99),
    quarterly: card("3 Months", 49.99),
    sixMonth: card("6 Months", 94.99),
  };

  it("takes each price from the plans on sale, matched by length and exam", () => {
    const live = [
      { exam_code: "sca", duration_days: 30, amount_pence: 2999 },
      { exam_code: "sca", duration_days: 90, amount_pence: 5999 },
      { exam_code: "plab", duration_days: 30, amount_pence: 1 },
    ];
    const out = livePricedPlans(cards, "sca", live);
    assert.deepEqual(Object.keys(out), ["trial", "monthly", "quarterly"]);
    assert.equal(out.monthly?.price, 29.99);
    assert.equal(out.quarterly?.price, 59.99);
    assert.equal(out.trial?.price, 0);
  });

  it("counts the stations a plan's exam has published, on the card and in its high-yield line", () => {
    const stationCards = {
      trial: { name: "Free Trial", price: 0, stations: 3, features: ["3 free trial stations"] },
      monthly: {
        name: "1 Month",
        price: 24.99,
        stations: "Full station library" as number | string,
        features: ["High-Yield Clinical Stations", "Video Presentations"],
      },
    };
    const live = [{ exam_code: "sca", duration_days: 30, amount_pence: 2999, station_count: 112 }];
    const out = livePricedPlans(stationCards, "sca", live);
    assert.equal(out.monthly?.stations, 112);
    assert.deepEqual(out.monthly?.features, ["112 High-Yield Clinical Stations", "Video Presentations"]);
    assert.equal(out.trial?.stations, 3);
    const none = livePricedPlans(stationCards, "sca", [{ ...live[0]!, station_count: 0 }]);
    assert.equal(none.monthly?.stations, "Full station library");
    assert.deepEqual(none.monthly?.features, ["High-Yield Clinical Stations", "Video Presentations"]);
  });

  it("drops a card with no plan on sale rather than showing an invented price", () => {
    assert.deepEqual(Object.keys(livePricedPlans(cards, "sca", [])), ["trial"]);
  });
});
