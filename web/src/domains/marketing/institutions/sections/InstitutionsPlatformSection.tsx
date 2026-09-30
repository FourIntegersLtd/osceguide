import { LandingIconBadge } from "@/domains/marketing/LandingIconBadge";
import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { B2bMarketingScreenshot } from "../components/B2bMarketingScreenshot";
import { PLATFORM_FEATURES } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

export function InstitutionsPlatformSection() {
  const type = institutionsLandingType;

  return (
    <section
      id="platform"
      className={`scroll-mt-20 ${landingSectionSurfaces.practice} py-16 sm:py-20`}
    >
      <div className={type.sectionShell}>
        <div className="grid gap-12 lg:grid-cols-12 lg:items-start">
          <div className="lg:col-span-5">
            <p className={type.eyebrow}>Platform</p>
            <h2 className="mt-3 font-landing-heading text-[clamp(1.375rem,2.4vw,1.75rem)] font-semibold leading-[1.2] tracking-[-0.025em] text-osce-ink-900">
              Everything in one place for your programme
            </h2>
            <ul className="mt-8 flex flex-col gap-4">
              {PLATFORM_FEATURES.map((feature) => (
                <li
                  key={feature.text}
                  className="font-landing-body flex items-center gap-3 text-sm font-medium text-b2c-text-secondary"
                >
                  <LandingIconBadge
                    icon={feature.icon}
                    color={feature.iconColor}
                    size="sm"
                  />
                  <span>{feature.text}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-7">
            <B2bMarketingScreenshot
              alt="Organisation dashboard with setup progress, sessions, and trainee roster"
              caption="See what is ready before you open the circuit, and what still needs attention."
              maxHeightClass="max-h-[min(480px,62vh)]"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
