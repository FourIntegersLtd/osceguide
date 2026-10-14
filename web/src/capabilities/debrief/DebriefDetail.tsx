"use client";

import { HiOutlineFaceFrown } from "react-icons/hi2";
import { AsyncBoundary, B2CEmptyState, Back, Card, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { asLines, readDebrief } from "@/capabilities/debrief/api";

const { b2cHeroCtaSurface, b2cMonoEyebrow, b2cPageTitle } = productTokens;

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
      <div className="space-y-3">
        <Back />
        <h1 className={b2cPageTitle}>Debrief details</h1>
      </div>
      <AsyncBoundary state={state}>
        {(debrief) =>
          debrief === null ? (
            <B2CEmptyState
              icon={HiOutlineFaceFrown}
              title="Debrief not found"
              description="It may have been deleted, or it belongs to another account."
            />
          ) : (
            <>
              <section className={`${b2cHeroCtaSurface} flex flex-col gap-1.5`}>
                <span className={b2cMonoEyebrow}>Narrative summary</span>
                <p className="max-w-[640px] text-[15px] leading-[24px] text-osce-ink-900">
                  {debrief.narrative ?? "No narrative was recorded for this debrief."}
                </p>
              </section>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <Card title="Key insights">
                  <ul className="divide-y divide-osce-border-light">
                    {asLines(debrief.key_insights).map((insight, index) => (
                      <li
                        key={index}
                        className="py-2.5 text-osce-body text-osce-ink-900 first:pt-0 last:pb-0"
                      >
                        {insight}
                      </li>
                    ))}
                  </ul>
                </Card>
                <Card title="Action plan">
                  <ol className="divide-y divide-osce-border-light">
                    {asLines(debrief.action_plan).map((action, index) => (
                      <li
                        key={index}
                        className="flex gap-4 py-2.5 text-osce-body text-osce-ink-900 first:pt-0 last:pb-0"
                      >
                        <span className="w-6 shrink-0 text-osce-meta tabular-nums text-b2c-text-muted">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        {action}
                      </li>
                    ))}
                  </ol>
                </Card>
              </div>
            </>
          )
        }
      </AsyncBoundary>
    </div>
  );
}
