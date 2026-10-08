import type { components } from "@/foundation/platform-client";

/**
 * A plan on sale, as `GET /billing/plans` answers it (the fields a price card needs).
 * `station_count` (published stations in the plan's exam) is declared here until
 * schema.d.ts is regenerated.
 */
export type LivePlan = Pick<components["schemas"]["PlanRead"], "exam_code" | "duration_days" | "amount_pence"> & {
  station_count?: number;
};

type Tier = "monthly" | "quarterly" | "sixMonth";

/** Which card a plan of this length belongs on. */
function tierOf(days: number): Tier {
  if (days <= 45) return "monthly";
  if (days <= 135) return "quarterly";
  return "sixMonth";
}

/** The card's station figures from the exam's published count, or left as written when it has none. */
function stationsOf(
  card: { stations?: number | string; features?: readonly string[] },
  count: number,
): { stations?: number; features?: readonly string[] } {
  if (count <= 0) return {};
  return {
    stations: count,
    features: card.features?.map((line) => line.replace(/^(?=High-Yield )/, `${count} `)),
  };
}

/**
 * The price cards for an exam, priced from the plans on sale.
 *
 * The cards carry the wording; the plan rows own the money. A paid card with
 * no plan behind it is dropped, because a price nobody can pay is worse than
 * a missing card. The free trial has no plan row and stays.
 */
export function livePricedPlans<T extends { price: number; stations?: number | string; features?: readonly string[] }>(
  cards: Record<string, T>,
  examCode: string,
  live: readonly LivePlan[],
): Record<string, T> {
  const out: Record<string, T> = {};
  for (const [key, card] of Object.entries(cards)) {
    if (key === "trial") {
      out[key] = card;
      continue;
    }
    const plan = live.find((p) => p.exam_code === examCode && tierOf(p.duration_days) === key);
    if (plan) out[key] = { ...card, ...stationsOf(card, plan.station_count ?? 0), price: plan.amount_pence / 100 };
  }
  return out;
}
