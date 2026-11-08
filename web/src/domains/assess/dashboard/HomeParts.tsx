"use client";

import Link from "next/link";
import { useSurface } from "@/capabilities";
import type { ReactNode } from "react";
import { LuCalendarDays, LuClipboardList, LuLayoutGrid, LuUserCheck, LuUsers } from "react-icons/lu";
import { ActionMenu, b2bTokens, cn, type ActionMenuItem } from "@/foundation/ui";
import { humanise } from "@/foundation/format";
import { boardBtn, boardChip } from "@/foundation/ui/boardKit";
import type { OrgSittingRow } from "@/domains/assess/dashboard/api";
import { dateTile, modeLabel, sittingTally, type HomeFocus, type WeekDay } from "@/domains/assess/dashboard/support";
import type { AssessWords } from "@/capabilities/assess-words";

const lift = "shadow-home-lift";

/**
 * The home hero: the date, the greeting, and the one thing to do now with its single action. Everything else
 * the screen offers sits in the quiet link and the "⋯" menu, so there is never a row of buttons. An empty
 * state is this card's sentence, not a box of its own.
 */
export function HomeHero({
  eyebrow,
  greeting,
  focus,
  href,
  clock,
  quietLink,
  menu,
}: {
  eyebrow: string;
  greeting: string;
  focus: HomeFocus;
  /** Maps a surface-relative path to its link. */
  href: (path: string) => string;
  clock?: ReactNode;
  quietLink?: { label: string; href: string } | null;
  menu: readonly ActionMenuItem[];
}) {
  const live = focus.kind === "running";
  return (
    <section
      aria-label="Today"
      className={cn(
        "flex flex-col gap-6 rounded-panel border border-osce-border bg-gradient-to-br to-osce-surface p-8 max-[900px]:gap-6 max-[900px]:p-5",
        live ? "from-assess-hero-live-bg" : "from-osce-canvas",
        lift,
      )}
    >
      <div>
        <div className={b2bTokens.assessEyebrow}>{eyebrow}</div>
        <h1 className={b2bTokens.assessTitle}>{greeting}</h1>
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          {live ? <span className={boardChip("live")}>Live</span> : null}
          <h2 className="text-assess-h2 font-semibold text-osce-ink-900 max-[900px]:text-assess-section">{focus.title}</h2>
        </div>
        <p className="max-w-[60ch] text-assess-desc text-osce-ink-500">{focus.body}</p>
        {clock ? <div className="text-assess-label tabular-nums text-osce-ink-700">{clock}</div> : null}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {focus.action ? (
          <Link href={href(focus.action.href)} className={boardBtn("primary")}>
            {focus.action.label}
          </Link>
        ) : null}
        {quietLink ? (
          <Link href={href(quietLink.href)} className={cn(b2bTokens.b2bLink, "text-assess-label")}>
            {quietLink.label}
          </Link>
        ) : null}
        {menu.length > 0 ? <ActionMenu items={menu} label="More" /> : null}
      </div>
    </section>
  );
}

/** Seven days from today as a calm strip; a day with a sitting is a link and carries a dot. */
export function WeekStrip({ days, href, sittingsLabel }: { days: readonly WeekDay[]; href: (path: string) => string; sittingsLabel: string }) {
  const any = days.some((day) => day.sittings.length > 0);
  return (
    <section aria-label="This week" className={cn("flex flex-col gap-3 rounded-panel border border-osce-border bg-osce-surface p-5", lift)}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-assess-label font-semibold text-osce-ink-900">This week</h2>
        {!any ? <span className={b2bTokens.assessMeta}>{`No ${sittingsLabel} in the next seven days`}</span> : null}
      </div>
      <ol className="grid grid-cols-7 gap-1.5">
        {days.map((day) => {
          const first = day.sittings[0];
          const body = (
            <>
              <span className={cn("text-assess-eyebrow uppercase", day.today ? "text-osce-accent" : "text-osce-ink-500")}>{day.weekday}</span>
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-assess-label font-semibold tabular-nums",
                  day.today ? "bg-osce-accent text-white" : "text-osce-ink-900",
                )}
              >
                {day.day}
              </span>
              <span aria-hidden className={cn("h-1.5 w-1.5 rounded-full", first ? "bg-osce-accent" : "bg-transparent")} />
            </>
          );
          const cls = "flex min-w-0 flex-col items-center gap-1 rounded-control py-2";
          return (
            <li key={day.key}>
              {first ? (
                <Link
                  href={href(day.sittings.length === 1 ? `/sittings/${first.id}` : "/sittings")}
                  aria-label={`${day.weekday} ${day.day}: ${day.sittings.map((s) => s.name).join(", ")}`}
                  className={cn(cls, "hover:bg-osce-canvas")}
                >
                  {body}
                </Link>
              ) : (
                <div className={cls}>{body}</div>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

const TILE_ICONS: Record<string, ReactNode> = {
  "/authoring/exams": <LuClipboardList aria-hidden />,
  "/authoring/stations": <LuLayoutGrid aria-hidden />,
  "/trainees": <LuUsers aria-hidden />,
  "/team": <LuUserCheck aria-hidden />,
  "/sittings": <LuCalendarDays aria-hidden />,
};

/** The counts as quiet linked tiles: an icon, the number, the name; each opens its list. */
export function StatTiles({ tiles }: { tiles: readonly { label: string; value: number; path: string }[] }) {
  return (
    <ul aria-label="At a glance" className="grid grid-cols-2 gap-3 min-[600px]:grid-cols-3 min-[1000px]:grid-cols-5">
      {tiles.map((tile) => (
        <li key={tile.label} className="contents">
          <TileLink tile={tile} />
        </li>
      ))}
    </ul>
  );
}


function TileLink({ tile }: { tile: { label: string; value: number; path: string } }) {
  const { hrefFor } = useSurface();
  return (
    <Link
      href={hrefFor(tile.path)}
      className="group flex flex-col gap-3 rounded-panel border border-osce-border bg-osce-surface p-4 hover:bg-osce-canvas focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent"
    >
      <span className="flex h-8 w-8 items-center justify-center rounded-control bg-osce-navActive text-assess-desc text-osce-accent">{TILE_ICONS[tile.path]}</span>
      <span className="flex flex-col gap-0.5">
        <span className={b2bTokens.assessMeta}>{tile.label}</span>
        <span className={b2bTokens.assessStatNumber}>{tile.value}</span>
      </span>
    </Link>
  );
}

/** One sitting as a rich row: a date block, the name, the mode chip and the status. */
export function SittingCard({ sitting, w, href, last }: { sitting: OrgSittingRow; w: AssessWords; href: string; last: boolean }) {
  const date = dateTile(sitting.scheduled_for);
  return (
    <Link
      href={href}
      className={cn("flex flex-wrap items-center gap-4 px-5 py-4 hover:bg-osce-canvas max-[900px]:gap-3", !last && "border-b border-osce-border-light")}
    >
      <div aria-hidden className="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-control bg-osce-navActive">
        <span className="text-assess-eyebrow uppercase text-osce-ink-500">{date?.month ?? "TBC"}</span>
        <span className="text-assess-desc font-semibold leading-none text-osce-ink-900">{date?.day ?? "-"}</span>
      </div>
      <div className="min-w-0 flex-[1_1_200px]">
        <div className="font-medium text-osce-ink-900">{sitting.name}</div>
        <div className={b2bTokens.assessMeta}>{sittingTally(sitting, w)}</div>
      </div>
      <span className={boardChip("neutral")}>{modeLabel(sitting.mode, w)}</span>
      <span className={boardChip(sitting.status === "scheduled" ? "info" : "neutral")}>{humanise(sitting.status)}</span>
    </Link>
  );
}
