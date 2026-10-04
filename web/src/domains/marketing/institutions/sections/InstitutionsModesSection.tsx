import { landingSectionSurfaces } from "@/domains/marketing/landingSectionSurfaces";
import { MarketingPill } from "../components/MarketingPill";
import { EXAM_BULLETS, TRAINING_BULLETS } from "../institutionsLandingContent";
import { institutionsLandingType } from "../institutionsLandingType";

function ModeCard({
  eyebrow,
  title,
  body,
  bullets,
  muted = false,
  footer,
}: {
  eyebrow: string;
  title: string;
  body: string;
  bullets: readonly string[];
  muted?: boolean;
  footer?: string;
}) {
  const type = institutionsLandingType;

  return (
    <article
      className={`flex flex-col gap-6 rounded-landing-card border border-landing-warm p-6 shadow-landing-card sm:p-8 ${
        muted ? "bg-landing-card-muted" : "bg-landing-card"
      }`}
    >
      <div>
        <p className={type.eyebrow}>{eyebrow}</p>
        <h3 className={`${type.itemTitle} mt-3`}>{title}</h3>
        <p className={`mt-3 ${type.itemBody}`}>{body}</p>
      </div>
      <ul className="flex flex-col gap-3">
        {bullets.map((item) => (
          <li
            key={item}
            className="font-landing-body flex items-center gap-3 text-sm font-medium text-b2c-text-secondary"
          >
            <span
              className="flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border border-osce-band-competentBorder bg-osce-band-competentBg"
              aria-hidden
            >
              <span className="h-1.5 w-1.5 rounded-[1px] bg-osce-band-competent" />
            </span>
            <span className="text-b2c-text-secondary">{item}</span>
          </li>
        ))}
      </ul>
      {footer ? (
        <p className={`border-t border-landing-hairline pt-4 ${type.itemBody}`}>
          {footer}
        </p>
      ) : null}
    </article>
  );
}

export function InstitutionsModesSection() {
  const type = institutionsLandingType;

  return (
    <section className={`${landingSectionSurfaces.plain} ${type.sectionPadding}`}>
      <div className={type.sectionShell}>
        <div className="mx-auto max-w-3xl text-center">
          <MarketingPill>Session types</MarketingPill>
          <h2 className={`${type.sectionTitle} mt-5`}>
            Training sessions and exam circuits
          </h2>
          <p className={type.sectionSubtitleCentered}>
            One platform for formative practice and formal assessment. Each mode
            follows your programme&apos;s rules.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <ModeCard
            eyebrow="Training sessions"
            title="Formative practice for your cohort"
            body="For skills weeks and prep sessions. Supervisors set the pace, take notes, and give feedback in exam-day format."
            bullets={TRAINING_BULLETS}
          />
          <ModeCard
            eyebrow="Exam circuits"
            title="Formal assessment on exam day"
            body="For assessment days. Supervisors observe only; feedback waits for examiner approval. Every station is logged."
            bullets={EXAM_BULLETS}
            muted
            footer="Summative use is a governance decision for your programme. We'll explain what the platform handles and where examiner oversight stays with faculty."
          />
        </div>
      </div>
    </section>
  );
}
