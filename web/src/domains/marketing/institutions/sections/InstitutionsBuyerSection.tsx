import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { MarketingPill } from "../components/MarketingPill";
import { BUYER_TYPES } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsBuyerSection() {
  const type = institutionsLandingType;

  return (
    <section
      id="for"
      className={`scroll-mt-20 ${landingSectionSurfaces.exams} ${type.sectionPadding}`}
    >
      <div className={type.sectionShell}>
        <MarketingPill>Who it&apos;s for</MarketingPill>
        <h2 className={`${type.sectionTitle} mt-5 max-w-[24ch]`}>
          Built for programmes that run OSCEs
        </h2>
        <p className={`${type.sectionSubtitle} max-w-[60ch]`}>
          Undergraduate, postgraduate, and workforce programmes on one platform.
          You bring stations and rubrics. We handle the rest.
        </p>

        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {BUYER_TYPES.map((buyer) => (
            <article
              key={buyer.label}
              className="rounded-landing-card border border-landing-warm bg-landing-card p-6 shadow-landing-card sm:p-7"
            >
              <h3 className={type.itemTitle}>{buyer.label}</h3>
              <p className={`mt-3 ${type.itemBody}`}>{buyer.description}</p>
              <ul className="mt-5 flex flex-col gap-2.5">
                {buyer.examples.map((example) => (
                  <li
                    key={example}
                    className={`${type.listItem} text-b2c-text-secondary`}
                  >
                    <span
                      className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-osce-accent"
                      aria-hidden
                    />
                    {example}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
