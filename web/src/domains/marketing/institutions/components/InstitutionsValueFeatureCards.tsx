import { LandingIconBadge } from "@/domains/marketing/LandingIconBadge";
import { VALUE_PROPS } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsValueFeatureCards() {
  const type = institutionsLandingType;

  return (
    <div className="mt-6 grid grid-cols-1 gap-6 sm:mt-10 sm:grid-cols-2 sm:gap-8 lg:grid-cols-3 lg:gap-10">
      {VALUE_PROPS.map((prop) => (
        <article key={prop.label} className="flex gap-3.5">
          <LandingIconBadge icon={prop.icon} color={prop.iconColor} />
          <div className="min-w-0 pt-0.5">
            <h3 className={type.itemTitle}>{prop.label}</h3>
            <p className={`mt-1.5 ${type.itemBody}`}>{prop.body}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
