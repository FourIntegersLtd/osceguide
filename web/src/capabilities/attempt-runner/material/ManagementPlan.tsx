"use client";

import type { ReactNode } from "react";
import { HiOutlineLightBulb } from "react-icons/hi2";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  cn,
  productTokens,
} from "@/foundation/ui";
import { Dropdown } from "@/foundation/table";
import type { AttemptReview } from "@/capabilities/attempt-runner/api";

const { b2cBodyText, b2cReadingTones, b2cSectionTitle } = productTokens;
type ToneKey = keyof typeof b2cReadingTones;

/**
 * What the candidate should have covered, read after the consultation.
 *
 * The retiring client's Management step, section for section: the patient's
 * information with their ideas, concerns and expectations called out, then the
 * plan — an explanation, the clinical assessment as a grid, and three
 * collapsible groups.
 *
 * `select-none` is the old screen's too. It does not stop anybody determined,
 * and it is not there to: it stops the reflex of dragging a model answer
 * straight into a revision note, which is the thing that makes this material
 * worth less to everybody.
 */
export function ManagementPlan({ review }: { review: AttemptReview }) {
  const patient = review.patient_information;
  const plan = review.management_plan;

  return (
    <div className="max-w-full select-none space-y-6 overflow-x-hidden sm:space-y-8">
      <h1 className={cn(productTokens.b2cPageTitle, "my-4 text-center sm:my-6")}>
        {review.station_title}
      </h1>

      {patient && (
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Patient information</B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
            {patient.patient_biodata && <InfoCard title="Biodata" text={patient.patient_biodata} />}

            {(patient.idea?.length ||
              patient.concerns?.length ||
              patient.expectation?.length) && (
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 text-osce-body font-medium text-osce-accent-hover">
                  <HiOutlineLightBulb className="h-4 w-4 shrink-0" aria-hidden />
                  ICE (Ideas, Concerns, Expectations)
                </h3>
                <div className="space-y-3">
                  <InfoCard title="Ideas" items={patient.idea} />
                  <InfoCard title="Concerns" items={patient.concerns} />
                  <InfoCard title="Expectations" items={patient.expectation} />
                </div>
              </div>
            )}
          </B2CPanelCardBody>
        </B2CPanelCard>
      )}

      {plan && (
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Management plan</B2CPanelCardHeader>
          <B2CPanelCardBody>
            {plan.explanation && (
              <InfoCard title="Explanation" text={plan.explanation} tone="management" />
            )}

            <Section title="Clinical Assessment">
              <Grid>
                <InfoCard
                  title="Differential Diagnosis"
                  items={plan.differential_diagnosis}
                  tone="reasoning"
                />
                <InfoCard
                  title="Examination Findings"
                  items={plan.examination_findings}
                  tone="examination"
                />
                <InfoCard title="Assessment Steps" items={plan.assessment} tone="reasoning" />
                <InfoCard
                  title="Further Investigations"
                  items={plan.further_investigations}
                  tone="examination"
                />
              </Grid>
            </Section>

            <Dropdown title="Social & Patient Concerns" className="mt-0">
              <Grid>
                <InfoCard title="Social Concerns" items={plan.social_concerns} tone="history" />
                <InfoCard title="ICE Response" items={plan.ice} tone="history" />
              </Grid>
            </Dropdown>

            <Dropdown title="Treatment & Actions" className="mt-0">
              <Grid>
                <InfoCard title="Immediate Actions" items={plan.immediate_actions} tone="safety" />
                <InfoCard
                  title="Medications"
                  items={plan.pharmacological_treatment}
                  tone="management"
                />
                <InfoCard
                  title="Non-Pharmacological Treatment"
                  items={plan.non_pharmacological_treatment}
                  tone="management"
                />
              </Grid>
            </Dropdown>

            <Dropdown title="Patient Education & Follow-up" className="mt-0">
              <Grid>
                <InfoCard
                  title="Health Education"
                  items={plan.health_education}
                  tone="education"
                />
                <InfoCard
                  title="Follow-up & Safety"
                  items={[plan.follow_up, plan.safety_netting].filter(Boolean) as string[]}
                  tone="safety"
                />
              </Grid>
            </Dropdown>

            {plan.additional_notes && (
              <Dropdown title="Additional Notes" className="mt-0">
                <InfoCard
                  title="Additional Notes"
                  text={plan.additional_notes}
                  tone="education"
                />
              </Dropdown>
            )}
          </B2CPanelCardBody>
        </B2CPanelCard>
      )}

      {!patient && !plan && (
        <p className="text-center text-osce-body text-b2c-text-muted">
          This station has no written model answer.
        </p>
      )}
    </div>
  );
}

/** One tinted card. Renders nothing at all when its section is empty. */
function InfoCard({
  title,
  items,
  text,
  tone = "history",
}: {
  title: string;
  items?: string[] | null;
  text?: string | null;
  tone?: ToneKey;
}) {
  const list = items ?? [];
  if (!text && list.length === 0) return null;

  const colours = b2cReadingTones[tone];
  return (
    <div className={cn("rounded-2xl border p-4", colours.card)}>
      <h4 className={cn("mb-2 text-osce-body font-medium", colours.title)}>{title}</h4>
      {text ? (
        <p className={b2cBodyText}>{text}</p>
      ) : (
        <ul className={cn("list-disc space-y-1.5 pl-5", colours.list)}>
          {list.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="my-6 space-y-4 sm:my-8 sm:space-y-6">
      <h3 className={cn(b2cSectionTitle, "border-b border-b2c-border pb-2")}>{title}</h3>
      {children}
    </div>
  );
}

/** Two columns on a very wide screen, one everywhere else. */
function Grid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-6 2xl:grid-cols-2">{children}</div>;
}
