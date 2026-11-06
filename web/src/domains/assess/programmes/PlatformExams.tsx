"use client";

import { useState } from "react";
import { AsyncBoundary, b2bTokens } from "@/foundation/ui";
import { boardAlert, boardCardClipped, boardRow, boardButtonSmall } from "@/foundation/ui/boardKit";
import { BoardChip, boardActs, boardMeta, boardStack } from "@/capabilities/authoring/parts/boardUi";
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
          <div className={boardStack}>
            {notice ? (
              <p role={notice.tone === "danger" ? "alert" : "status"} className={boardAlert(notice.tone === "danger" ? "bad" : "ok")}>
                {notice.text}
              </p>
            ) : null}
            <h2 className={`m-0 ${b2bTokens.assessEyebrow}`}>Exams the platform publishes</h2>
            <div className={boardCardClipped}>
              {data.items.map((exam, index) => (
                <div key={exam.exam_id} data-row className={`${boardRow} ${index === 0 ? "border-t-0" : ""}`}>
                  <span className="min-w-[260px] flex-[1_1_260px]">
                    <b className="font-semibold">{exam.title}</b>
                    <div className={boardMeta}>{`${exam.code} · ${exam.station_count} library ${exam.station_count === 1 ? "station" : "stations"}`}</div>
                  </span>
                  <div className={boardActs}>
                    {exam.already_imported ? (
                      <BoardChip tone="ok">Adopted</BoardChip>
                    ) : mayAdopt ? (
                      <button type="button" className={boardButtonSmall} disabled={busy !== null} onClick={() => void adopt(exam.exam_id, exam.title)}>
                        {busy === exam.exam_id ? "Adopting…" : "Adopt"}
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      }
    </AsyncBoundary>
  );
}
