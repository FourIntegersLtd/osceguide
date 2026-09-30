"use client";

import { HiOutlineFaceFrown } from "react-icons/hi2";
import {
  HiOutlineClipboardList,
  HiOutlineDocumentText,
  HiOutlineLightBulb,
} from "react-icons/hi";
import { AsyncBoundary, B2CEmptyState, Back, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { asLines, readDebrief } from "@/capabilities/debrief/api";

const { b2cPageTitle, b2cPanelDivided, b2cPanelSection } = productTokens;

function Section({
  icon,
  iconWellClassName,
  title,
  children,
}: {
  icon: React.ReactNode;
  iconWellClassName: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className={b2cPanelSection}>
      <div className="mb-3 flex items-center gap-3">
        <div className={`rounded-full p-2 ${iconWellClassName}`}>{icon}</div>
        <h2 className="text-osce-body font-semibold text-osce-ink-900">{title}</h2>
      </div>
      {children}
    </div>
  );
}

/**
 * What one debrief concluded.
 *
 * Three parts, in the order the tutor speaks them: what happened, what it
 * means, and what to do about it. The last is the one the tutor reads back at
 * the start of the next session, which is why it is a list of agreed actions
 * rather than prose.
 */
export function DebriefDetail({ id }: { id: string }) {
  const state = useAsync((signal) => readDebrief(id, signal), [id]);

  return (
    <div className="space-y-6">
      <Back />
      <h1 className={b2cPageTitle}>Debrief Details</h1>
      <AsyncBoundary state={state}>
        {(debrief) =>
          debrief === null ? (
            <B2CEmptyState
              icon={HiOutlineFaceFrown}
              title="Debrief Not Found"
              description="The requested debrief could not be found."
            />
          ) : (
            <div className={b2cPanelDivided}>
              <Section
                icon={<HiOutlineDocumentText className="h-5 w-5 text-osce-accent" />}
                iconWellClassName="bg-osce-accent-subtle"
                title="Narrative Summary"
              >
                <p className="leading-relaxed text-b2c-text-secondary">
                  {debrief.narrative ?? "No narrative was recorded for this debrief."}
                </p>
              </Section>
              <Section
                icon={<HiOutlineLightBulb className="h-5 w-5 text-osce-warning-icon" />}
                iconWellClassName="bg-osce-warning-bg"
                title="Key Insights"
              >
                <ul className="list-inside list-disc space-y-2 text-b2c-text-secondary">
                  {asLines(debrief.key_insights).map((insight, index) => (
                    <li key={index}>{insight}</li>
                  ))}
                </ul>
              </Section>
              <Section
                icon={<HiOutlineClipboardList className="h-5 w-5 text-osce-success-icon" />}
                iconWellClassName="bg-osce-success-bg"
                title="Action Plan"
              >
                <ul className="list-inside list-disc space-y-2 text-b2c-text-secondary">
                  {asLines(debrief.action_plan).map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              </Section>
            </div>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
