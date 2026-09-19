import { B2CPanelCard, B2CPanelCardBody, B2CPanelCardHeader, productTokens } from "@/foundation/ui";
import type { PriorityAction } from "@/capabilities/feedback/model";

const { b2cBodyText, b2cSectionTitle } = productTokens;

/**
 * The three or four things to fix first.
 *
 * Kept as its own section rather than folded into the domain cards: it is the
 * only part of the mark that crosses domains, and it is what a person reads
 * when they have time for one thing before the next station.
 */
export function FeedbackPriorityAreas({ priorities }: { priorities: PriorityAction[] }) {
  if (priorities.length === 0) return null;

  return (
    <div>
      <h2 className={`${b2cSectionTitle} mb-4 mt-10 text-center`}>Key Priority Areas</h2>
      <div className="space-y-4">
        {priorities.map((priority, index) => (
          <B2CPanelCard key={`${priority.area}-${index}`} className="mt-0">
            <B2CPanelCardHeader>
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-osce-accent text-osce-caption font-semibold text-white">
                {index + 1}
              </span>
              {priority.area}
            </B2CPanelCardHeader>
            <B2CPanelCardBody>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-md bg-osce-danger-bg p-4">
                  <h4 className="mb-2 flex items-center gap-2 text-osce-body font-medium text-osce-danger-hover">
                    <span className="h-2 w-2 rounded-full bg-osce-danger" />
                    Current Level
                  </h4>
                  <p className={b2cBodyText}>{priority.currentLevel || "No current level generated"}</p>
                </div>
                <div className="rounded-md bg-osce-success-bg p-4">
                  <h4 className="mb-2 flex items-center gap-2 text-osce-body font-medium text-osce-success-text">
                    <span className="h-2 w-2 rounded-full bg-osce-success-icon" />
                    Expected Outcome
                  </h4>
                  <p className={b2cBodyText}>
                    {priority.expectedOutcome || "No expected outcome generated"}
                  </p>
                </div>
                <div className="rounded-md bg-osce-accent-muted p-4">
                  <h4 className="mb-2 flex items-center gap-2 text-osce-body font-medium text-osce-accent-hover">
                    <span className="h-2 w-2 rounded-full bg-osce-accent" />
                    Improvement Steps
                  </h4>
                  <ul className="space-y-2">
                    {priority.steps.length > 0 ? (
                      priority.steps.map((step, stepIndex) => (
                        <li key={stepIndex} className={`flex items-start gap-2 ${b2cBodyText}`}>
                          <span className="text-osce-accent-light">→</span>
                          {step}
                        </li>
                      ))
                    ) : (
                      <li className={b2cBodyText}>No improvement steps generated</li>
                    )}
                  </ul>
                </div>
              </div>
            </B2CPanelCardBody>
          </B2CPanelCard>
        ))}
      </div>
    </div>
  );
}
