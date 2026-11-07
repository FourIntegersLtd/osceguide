"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { MicrophoneCheck } from "@/foundation/livekit";
import { b2bTokens as t } from "@/foundation/ui";
import { boardChip } from "@/foundation/ui/boardKit";
import { readMySittings } from "@/domains/assess/trainee/api";
import {
  TraineeHead,
  TraineeList,
  TraineePage,
  TraineeRow,
} from "@/domains/assess/trainee/traineeBoard";
import {
  browserEnv,
  browserVerdict,
  connectionVerdict,
  type CheckResult,
} from "@/domains/assess/trainee/setupChecks";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * "Test your setup": the candidate's own page, reached from their invitation and reminder emails and
 * from their assessment. It checks the microphone, the browser and the connection, and shows nothing
 * about the person: the address carries no token or id, and the connection test is the same signed-in
 * read their assessment page makes (`/me/sittings`), so being signed in is what identifies them.
 */
export function TechCheck() {
  const w = useAssessWords();
  const { orgSlug, hrefFor } = useSurface();
  const [browser, setBrowser] = useState<CheckResult | null>(null);
  const [connection, setConnection] = useState<CheckResult | null>(null);
  const [testing, setTesting] = useState(false);

  const run = useCallback(async () => {
    setTesting(true);
    setBrowser(browserVerdict(browserEnv()));
    const started = performance.now();
    let roundTrip: number | null = null;
    try {
      await readMySittings(orgSlug);
      roundTrip = performance.now() - started;
    } catch {
      roundTrip = null;
    }
    setConnection(connectionVerdict(navigator.onLine, roundTrip));
    setTesting(false);
  }, [orgSlug]);

  useEffect(() => {
    // The browser and the network live outside React, so the checks start on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void run();
  }, [run]);

  return (
    <TraineePage label="Test your setup">
      <div>
        <Link href={hrefFor("/trainee")} className="text-assess-label text-osce-accent">
          ‹ All {w.sittings}
        </Link>
      </div>
      <TraineeHead
        title="Test your setup"
        desc={`Check your microphone, browser and connection before your ${w.sitting}. It takes under a minute and nothing is recorded.`}
        acts={
          <Button themeType="b2b" variant="secondary" size="sm" onClick={() => void run()} isLoading={testing}>
            Test again
          </Button>
        }
      />
      <TraineeList title="Microphone">
        <MicrophoneCheck variant="plain" />
      </TraineeList>
      <TraineeList title="Browser and connection">
        <Row label="Browser" result={browser} />
        <Row label="Connection" result={connection} />
      </TraineeList>
    </TraineePage>
  );
}

function Row({ label, result }: { label: string; result: CheckResult | null }) {
  return (
    <TraineeRow title={result?.title ?? `Checking your ${label.toLowerCase()}…`} meta={result?.detail}>
      <span className={result ? boardChip(result.ok ? "ok" : "warn") : t.assessMeta}>
        {result ? (result.ok ? "Ready" : "Needs attention") : label}
      </span>
    </TraineeRow>
  );
}
