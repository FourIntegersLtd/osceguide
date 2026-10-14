"use client";

import { Card } from "@/foundation/ui";
import { MicrophoneCheck } from "@/foundation/livekit";
import type { Exam } from "@/capabilities/stations";
import { mockRules } from "@/domains/train/mocks/model";

/**
 * What happens next, before the clock starts (canvas `train-session`).
 *
 * Every number on this screen is the exam's: reading length, consultation
 * length, how many attempts a station allows. The retiring client kept eight
 * constants in `constants.ts` (`SCA_DOCTOR_TIMER_DURATION` and its siblings)
 * and a hardcoded `ALLOWED_STATION_ATTEMPTS = 3`, which meant an exam whose
 * timings changed on the backend went on advertising the old ones here.
 *
 * The start button lives in the session's hero, so the microphone's readiness
 * is reported up rather than owned here.
 */
export function MockRules({
  exam,
  onMicReadyChange,
}: {
  exam: Exam | null;
  onMicReadyChange: (ready: boolean) => void;
}) {
  const attemptLimit = exam?.station_attempt_limit ?? 3;

  const rules = mockRules(attemptLimit);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <Card title="Rules">
        <ol className="divide-y divide-osce-border-light">
          {rules.map((rule, index) => (
            <li key={rule} className="flex gap-4 py-3 first:pt-0 last:pb-0">
              <span className="w-6 shrink-0 text-osce-meta tabular-nums text-b2c-text-muted">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-osce-body leading-relaxed text-osce-ink-900">{rule}</span>
            </li>
          ))}
        </ol>
      </Card>
      <Card title="Microphone check">
        <MicrophoneCheck variant="plain" className="!p-0" onReadyChange={onMicReadyChange} />
      </Card>
    </div>
  );
}
