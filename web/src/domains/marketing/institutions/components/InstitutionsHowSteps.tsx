import { LandingIconBadge } from "@/domains/marketing/LandingIconBadge";
import { HOW_IT_WORKS_STEPS } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsHowSteps() {
  const type = institutionsLandingType;

  return (
    <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {HOW_IT_WORKS_STEPS.map((step) => (
        <article
          key={step.step}
          className="flex flex-col gap-4 rounded-landing-card border border-landing-warm bg-landing-card p-6 shadow-landing-card"
        >
          <p className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-b2c-text-muted">
            {step.step}
          </p>
          <LandingIconBadge icon={step.icon} color={step.iconColor} size="sm" />
          <div>
            <h3 className={type.itemTitle}>{step.title}</h3>
            <p className={`mt-2 ${type.itemBody}`}>{step.body}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
