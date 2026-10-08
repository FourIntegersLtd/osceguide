import type { Plan } from "@/capabilities/account/api";
import { normalizeExamCode } from "@/foundation/session/examSelection";

/**
 * The plans a signed-in account may buy: the exam the server holds for it, and
 * nothing the browser remembers. A localStorage selection (the landing page's,
 * or the switcher's) is navigation context; checkout refuses another exam's plan
 * (`billing/service_checkout.py`), so filtering by it offered plans that would
 * only fail. With no exam on the account every plan is on offer.
 */
export function plansForAccount(plans: Plan[], serverExamCode: string | null | undefined): Plan[] {
  const exam = normalizeExamCode(serverExamCode);
  return exam === null ? plans : plans.filter((plan) => plan.exam_code === exam);
}
