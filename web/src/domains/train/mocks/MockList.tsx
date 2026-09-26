"use client";

import { AsyncBoundary, Back, B2CPageHeader } from "@/foundation/ui";
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
  const state = useAsync(async (signal) => {
    const [sets, exams] = await Promise.all([listSets(signal), listExams(signal)]);
    return { sets: sets.items, exams: exams.items };
  }, []);

  return (
    <>
      <Back />
      <AsyncBoundary state={state}>
        {({ sets, exams }) => (
          <>
            <B2CPageHeader title={`${(examCode ?? "").toUpperCase()} Sessions`} />
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
