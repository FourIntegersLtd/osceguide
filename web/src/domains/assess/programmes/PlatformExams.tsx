"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Badge, B2CGroupedRow, B2CGroupedSection, Button } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { importPlatformExam, listPlatformCatalogue } from "@/domains/assess/programmes/api";
import { adoptRefusal } from "@/domains/assess/programmes/support";

/**
 * The exams the platform publishes, each one adoptable by reference: adopting
 * records an active programme naming the exam, so the organisation can
 * schedule against it without writing its own. `onAdopted` lets the page
 * refresh the programme list below.
 */
export function PlatformExams({ orgSlug, onAdopted }: { orgSlug: string; onAdopted: () => void }) {
  const { session } = useSession();
  const [reload, setReload] = useState(0);
  const catalogue = useAsync((signal) => listPlatformCatalogue(orgSlug, signal), [orgSlug, reload]);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const mayAdopt = can(session, "schedule_sittings");

  async function adopt(examId: string, title: string) {
    setBusy(examId);
    setNotice(null);
    try {
      await importPlatformExam(orgSlug, examId);
      setNotice({ tone: "success", text: `${title} is now one of your programmes. Schedule a sitting against it whenever you are ready.` });
      setReload((n) => n + 1);
      onAdopted();
    } catch (cause) {
      const refusal = adoptRefusal(cause);
      setNotice({ tone: "danger", text: refusal ?? errorMessage(cause) });
      // Both refusals mean the list on screen is out of date.
      if (refusal) setReload((n) => n + 1);
    } finally {
      setBusy(null);
    }
  }

  return (
    <AsyncBoundary state={catalogue}>
      {(data) =>
        data.items.length === 0 ? null : (
          <div className="flex flex-col gap-3">
            {notice ? <Alert tone={notice.tone}>{notice.text}</Alert> : null}
            <B2CGroupedSection eyebrow="Exams the platform publishes">
              {data.items.map((exam) => (
                <B2CGroupedRow
                  key={exam.exam_id}
                  title={exam.title}
                  meta={`${exam.code} · ${exam.station_count} library ${exam.station_count === 1 ? "station" : "stations"}`}
                  trailing={
                    exam.already_imported ? (
                      <Badge tone="success">Adopted</Badge>
                    ) : mayAdopt ? (
                      <Button
                        themeType="b2b"
                        variant="secondary"
                        size="sm"
                        disabled={busy !== null}
                        onClick={() => void adopt(exam.exam_id, exam.title)}
                      >
                        {busy === exam.exam_id ? "Adopting…" : "Adopt"}
                      </Button>
                    ) : null
                  }
                />
              ))}
            </B2CGroupedSection>
          </div>
        )
      }
    </AsyncBoundary>
  );
}
