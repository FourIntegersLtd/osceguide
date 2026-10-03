"use client";

import { AsyncBoundary, B2CPageHeader, ButtonLink } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { listExams } from "@/capabilities/stations";
import { listSets } from "@/domains/train/api";
import { MockSessions } from "@/domains/train/mocks/MockSessions";

/**
 * "View All Sessions": every session this person has for the exam they are
 * sitting, as the retiring client's `/mocks/list` showed them.
 */
export function MockList() {
  const { code: examCode } = useCurrentExam();
  const { hrefFor } = useSurface();
  const state = useAsync(async (signal) => {
    const [sets, exams] = await Promise.all([listSets(signal), listExams(signal)]);
    return { sets: sets.items, exams: exams.items };
  }, []);

  return (
    <>
      <B2CPageHeader
        back={{ href: hrefFor("/mocks"), label: "Practice" }}
        title={`${(examCode ?? "").toUpperCase()} sessions`}
        action={
          <ButtonLink href={hrefFor("/mocks")} variant="primary" size="md">
            New session
          </ButtonLink>
        }
      />
      <AsyncBoundary state={state}>
        {({ sets, exams }) => (
          <>
            <MockSessions
              sets={sets.filter((set) => set.exam_code === examCode)}
              exams={exams}
              onChanged={state.reload}
            />
          </>
        )}
      </AsyncBoundary>
    </>
  );
}
