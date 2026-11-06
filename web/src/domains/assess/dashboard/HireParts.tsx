"use client";

import { boardButtonSmall, boardPad } from "@/foundation/ui/boardKit";
import Link from "next/link";
import type { ReactNode } from "react";
import { b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import type { AttentionItem } from "@/domains/assess/dashboard/support";

/** The hire overview's header and attention card, drawn from the HireHome board. */
export function HireHeader({ name, words, action }: { name: string; words: ReturnType<typeof useAssessWords>; action: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className={b2bTokens.assessEyebrow}>{name}</div>
        <h1 className={b2bTokens.assessTitle}>Overview</h1>
        <p className={b2bTokens.assessDesc}>{`Your ${words.sittings}, ${words.trainees} and results.`}</p>
      </div>
      {action ? <div className="flex flex-wrap items-center gap-2.5">{action}</div> : null}
    </div>
  );
}

export function HireAttention({ items }: { items: AttentionItem[] }) {
  const { hrefFor } = useSurface();
  return (
    <div className={boardPad}>
      <h2 className="text-assess-desc font-semibold text-osce-ink-900">Needs your attention</h2>
      {items.length === 0 ? (
        <p className="border-t border-osce-border-light py-2.5 text-assess-label text-osce-ink-900">
          {"Nothing needs you right now. "}
          <Link href={hrefFor("/results")} className={b2bTokens.b2bLink}>
            Open Results
          </Link>
        </p>
      ) : (
        items.map((item) => (
          <Link key={item.key} href={hrefFor(item.href)} className="flex flex-wrap items-center gap-4 border-t border-osce-border-light py-2.5 text-assess-label text-osce-ink-900">
            <span className="flex-1">{item.title}</span>
            <span className={boardButtonSmall}>{item.tag}</span>
          </Link>
        ))
      )}
    </div>
  );
}
