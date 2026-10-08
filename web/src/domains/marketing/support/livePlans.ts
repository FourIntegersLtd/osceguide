/** A plan on sale, as `GET /billing/plans` answers it (the fields a price card needs). */
export interface LivePlan {
  exam_code: string;
  duration_days: number;
  amount_pence: number;
}

type Tier = "monthly" | "quarterly" | "sixMonth";

/** Which card a plan of this length belongs on. */
function tierOf(days: number): Tier {
  if (days <= 45) return "monthly";
  if (days <= 135) return "quarterly";
  return "sixMonth";
}

/**
 * The price cards for an exam, priced from the plans on sale.
 *
 * The cards carry the wording; the plan rows own the money. A paid card with
 * no plan behind it is dropped, because a price nobody can pay is worse than
 * a missing card. The free trial has no plan row and stays.
 */
export function livePricedPlans<T extends { price: number }>(
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
    if (plan) out[key] = { ...card, price: plan.amount_pence / 100 };
  }
  return out;
}
