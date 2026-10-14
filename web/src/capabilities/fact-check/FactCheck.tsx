"use client";

import { useState } from "react";
import type { IconType } from "react-icons";
import {
  HiOutlineChevronRight,
  HiOutlineDocumentText,
  HiOutlineGlobeAlt,
  HiOutlineShieldCheck,
} from "react-icons/hi";
import {
  Alert,
  B2CSegmentedTabs,
  Badge,
  Button,
  Textarea,
} from "@/foundation/ui";
import { cn } from "@/foundation/ui/cn";
import {
  isRemoval,
  needsRuling,
  placeOf,
  type Evidence,
  type FactClaim,
  type Facts,
  type Swap,
} from "@/capabilities/fact-check/facts";

type Tone = "success" | "danger" | "warning" | "neutral";
type TabId = "resolve" | "unconfirmed" | "supported" | "resolved";

const TABS: { id: TabId; label: string; empty: string }[] = [
  {
    id: "resolve",
    label: "To resolve",
    empty: "No source contradicts it.",
  },
  {
    id: "unconfirmed",
    label: "Unconfirmed",
    empty: "Every claim was found in at least one source.",
  },
  { id: "supported", label: "Supported", empty: "No claim is supported yet." },
  {
    id: "resolved",
    label: "Resolved",
    empty: "No correction has been accepted or dismissed yet.",
  },
];

function tabOf(claim: FactClaim): TabId {
  if (claim.decision) return "resolved";
  if (needsRuling(claim)) return "resolve";
  return claim.verdict === "supported" ? "supported" : "unconfirmed";
}

/** The two places a claim is looked up, labelled as Clinical Buddy labels them. */
const SOURCES: {
  kind: Evidence["kind"];
  checked: string;
  label: string;
  icon: IconType;
}[] = [
  {
    kind: "guideline",
    checked: "guidelines",
    label: "Guideline library",
    icon: HiOutlineDocumentText,
  },
  {
    kind: "web",
    checked: "web",
    label: "Clinical web",
    icon: HiOutlineGlobeAlt,
  },
];

const NOTHING: { label: string; tone: Tone } = {
  label: "Nothing found",
  tone: "neutral",
};
const SAID: Record<string, { label: string; tone: Tone }> = {
  supported: { label: "Supports", tone: "success" },
  contradicted: { label: "Contradicts", tone: "danger" },
  not_found: NOTHING,
};

const RELIABILITY: Record<string, { label: string; tone: Tone }> = {
  Reliable: { label: "Reliable", tone: "success" },
  Standard: { label: "Standard", tone: "neutral" },
  Low: { label: "Other", tone: "neutral" },
};

function when(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

/**
 * What one source said. Checks stored before both sources were always asked carry no
 * per-source verdict, so their evidence takes the claim's own.
 */
function findingOf(claim: FactClaim, kind: Evidence["kind"], checked: string) {
  const evidence = claim.evidence.find((entry) => entry.kind === kind) ?? null;
  const asked = evidence !== null || claim.checked.includes(checked);
  const verdict = evidence?.verdict ?? (evidence ? claim.verdict : "not_found");
  return { evidence, asked, said: SAID[verdict] ?? NOTHING };
}

function SourceCell({
  claim,
  kind,
  checked,
  label,
  icon: Icon,
}: (typeof SOURCES)[number] & { claim: FactClaim }) {
  const { evidence, asked, said } = findingOf(claim, kind, checked);
  const reliability = evidence?.reliability
    ? RELIABILITY[evidence.reliability]
    : undefined;

  return (
    <div className="flex min-w-0 flex-col gap-2 rounded-osce-md bg-canvas p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-osce-meta font-medium text-ink">
          <Icon className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
          {label}
        </span>
        {asked ? (
          <Badge tone={said.tone}>{said.label}</Badge>
        ) : (
          <Badge>Not asked</Badge>
        )}
      </div>
      {evidence?.quote ? (
        <p className="text-osce-meta text-ink">“{evidence.quote}”</p>
      ) : evidence?.why ? (
        <p className="text-osce-meta text-ink-subtle">{evidence.why}</p>
      ) : (
        <p className="text-osce-meta text-ink-subtle">
          {asked
            ? "Nothing here settles this claim."
            : "This source was not asked."}
        </p>
      )}
      {evidence?.source ? (
        <div className="flex min-w-0 flex-col gap-1.5">
          <span className="truncate text-osce-meta text-ink-subtle">
            {evidence.url ? (
              <a
                href={evidence.url}
                target="_blank"
                rel="noreferrer"
                className="text-ink hover:underline"
              >
                {evidence.source}
              </a>
            ) : (
              evidence.source.replace(/\.pdf$/i, "")
            )}
            {evidence.section ? ` · ${evidence.section}` : ""}
            {evidence.page !== null ? ` · page ${evidence.page}` : ""}
          </span>
          {reliability || evidence.source_type ? (
            <span className="flex flex-wrap gap-1.5">
              {reliability ? (
                <Badge tone={reliability.tone}>
                  {evidence.reliability === "Reliable" ? (
                    <HiOutlineShieldCheck className="h-3 w-3" aria-hidden />
                  ) : null}
                  {reliability.label}
                </Badge>
              ) : null}
              {evidence.source_type ? (
                <Badge>{evidence.source_type}</Badge>
              ) : null}
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

type Rulings = {
  /** `swap` is null when the reader made the change by hand. */
  onAccept: (claim: FactClaim, swap: Swap | null) => void;
  onDismiss: (claim: FactClaim) => void;
  /** Takes a ruling back: an accepted correction's words come out again. */
  onReopen: (claim: FactClaim) => void;
};

function Correction({
  claim,
  onAccept,
  onDismiss,
}: { claim: FactClaim } & Rulings) {
  const from = claim.suggestion?.old ?? null;
  const [to, setTo] = useState(claim.suggestion?.new ?? from ?? "");
  const where = placeOf(claim)?.toLowerCase() ?? "the content";

  return (
    <div className="flex flex-col gap-3 rounded-osce-md border border-border p-3">
      <p className="text-osce-meta font-medium text-ink">Your decision</p>
      {!claim.suggestion ? (
        <p className="text-osce-meta text-ink-subtle">
          The sources disagree with each other. Read both, then change {where}{" "}
          yourself and mark it fixed, or keep it.
        </p>
      ) : from ? (
        <>
          <p className="text-osce-meta text-ink">
            <span className="block text-osce-caption text-ink-subtle">
              On {where} now
            </span>
            “{from}”
          </p>
          <Textarea
            label="Change it to"
            rows={3}
            value={to}
            onChange={(event) => setTo(event.target.value)}
          />
        </>
      ) : (
        <p className="text-osce-meta text-ink-subtle">
          Suggested: {claim.suggestion.new}. This check is older than the
          one-click fix: check again to have it point at the line, or change{" "}
          {where} yourself and mark it fixed.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {from ? (
          <>
            <Button
              size="sm"
              disabled={!to.trim() || to.trim() === from}
              onClick={() => onAccept(claim, { from, to: to.trim() })}
            >
              Make this change
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onAccept(claim, { from, to: "" })}
            >
              Remove it
            </Button>
          </>
        ) : (
          <Button size="sm" onClick={() => onAccept(claim, null)}>
            Mark as fixed
          </Button>
        )}
        <Button size="sm" variant="outline" onClick={() => onDismiss(claim)}>
          Keep as written
        </Button>
      </div>
    </div>
  );
}

function Reopen({
  claim,
  onReopen,
}: {
  claim: FactClaim;
  onReopen: Rulings["onReopen"];
}) {
  // Corrections swapped in before the swap was recorded, and removed words, cannot be swapped back.
  const removed = isRemoval(claim.swap);
  const stuck =
    claim.decision === "accepted" &&
    Boolean(claim.suggestion?.old) &&
    (!claim.swap || removed);
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button size="sm" variant="outline" onClick={() => onReopen(claim)}>
        {claim.swap && !removed ? "Undo correction" : "Reopen"}
      </Button>
      {stuck ? (
        <span className="text-osce-caption text-ink-subtle">
          {removed
            ? "The removed words stay out; add them back yourself if needed."
            : "The corrected words stay; edit them back yourself if needed."}
        </span>
      ) : null}
    </div>
  );
}

function ClaimRow({
  claim,
  defaultOpen,
  rulings,
}: {
  claim: FactClaim;
  defaultOpen: boolean;
  /** Absent where the material is read only, so nothing can be ruled on. */
  rulings?: Rulings;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const place = placeOf(claim);

  return (
    <li className="px-5 py-4 sm:px-6">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-3 text-left"
      >
        <HiOutlineChevronRight
          className={cn(
            "mt-1 h-4 w-4 shrink-0 text-ink-subtle transition-transform",
            open && "rotate-90",
          )}
          aria-hidden
        />
        <span className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="flex flex-wrap items-center gap-2 text-osce-caption text-ink-subtle">
            {place ? <span>{place}</span> : null}
            {claim.verdict === "conflict" ? (
              <Badge tone="warning">Sources disagree</Badge>
            ) : null}
            {claim.decision ? (
              <Badge>
                {claim.decision === "accepted"
                  ? claim.by === "agent"
                    ? "Corrected by the agent"
                    : isRemoval(claim.swap)
                      ? "Removed"
                      : "Correction made"
                  : "Kept as written"}
              </Badge>
            ) : null}
          </span>
          <span className="text-osce-body text-ink">{claim.claim}</span>
          {!open ? (
            <span className="flex flex-wrap gap-3 text-osce-caption text-ink-subtle">
              {SOURCES.map(({ kind, checked, label, icon: Icon }) => {
                const { asked, said } = findingOf(claim, kind, checked);
                return (
                  <span key={kind} className="flex items-center gap-1">
                    <Icon className="h-3.5 w-3.5" aria-hidden />
                    {label}: {asked ? said.label.toLowerCase() : "not asked"}
                  </span>
                );
              })}
            </span>
          ) : null}
        </span>
      </button>
      {open ? (
        <div className="mt-3 flex flex-col gap-3 pl-7">
          {claim.why ? (
            <p className="text-osce-meta text-ink-subtle">{claim.why}</p>
          ) : null}
          <div className="grid gap-2 md:grid-cols-2">
            {SOURCES.map((source) => (
              <SourceCell key={source.kind} claim={claim} {...source} />
            ))}
          </div>
          {rulings && needsRuling(claim) ? (
            <Correction claim={claim} {...rulings} />
          ) : null}
          {rulings && claim.decision ? (
            <Reopen claim={claim} onReopen={rulings.onReopen} />
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

/**
 * Each clinical claim against the guideline library and the clinical web, side
 * by side, sorted into what needs a decision, what no source confirms, and what
 * is settled. The caller owns the material: it runs the check and applies a ruling.
 */
export function FactCheck({
  facts,
  locked,
  working = false,
  onCheck,
  rulings,
}: {
  facts: Facts | null;
  /** Disables the check, e.g. while edits the server has not been sent are open. */
  locked: boolean;
  working?: boolean;
  onCheck: () => void;
  /** Leave out where the material cannot be edited. */
  rulings?: Rulings;
}) {
  const claims = facts?.claims ?? [];
  const progress = working ? facts?.progress : undefined;
  // A ruling made while the check runs would be overwritten when it finishes.
  const ruling = working ? undefined : rulings;
  const counts = Object.fromEntries(
    TABS.map((tab) => [
      tab.id,
      claims.filter((claim) => tabOf(claim) === tab.id).length,
    ]),
  ) as Record<TabId, number>;
  const [chosen, setChosen] = useState<TabId | null>(null);
  const tab =
    chosen ?? TABS.find((entry) => counts[entry.id] > 0)?.id ?? "resolve";
  const shown = claims.filter((claim) => tabOf(claim) === tab);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <p className="min-w-0 max-w-prose text-osce-meta text-ink-subtle">
          {progress
            ? `${progress.done} of ${progress.total} claims checked so far. You can act on them once all are in.`
            : facts
              ? `${claims.length} claims, checked ${when(facts.checked_at)} against the guideline library and the clinical web. Nothing changes unless you accept a correction.`
              : "Each claim is looked up in the guideline library and on the clinical web. Nothing changes unless you accept a correction."}
        </p>
        {/* The first check starts from the screen's next-step bar; this one runs it again. */}
        {facts ? (
          <Button size="sm" variant="ghost" disabled={locked} isLoading={working} onClick={onCheck}>
            {working ? "Checking facts…" : "Check again"}
          </Button>
        ) : null}
      </div>

      {facts && claims.length > 0 ? (
        <>
          <B2CSegmentedTabs
            aria-label="Claims"
            compact
            value={tab}
            onChange={setChosen}
            items={TABS.map((entry) => ({
              id: entry.id,
              label: `${entry.label} ${counts[entry.id]}`,
            }))}
          />
          {!progress &&
          tab === "resolve" &&
          counts.resolve === 0 &&
          counts.unconfirmed === 0 ? (
            <Alert tone="success">Every claim is supported by a source.</Alert>
          ) : null}
          {shown.length > 0 ? (
            <div className="overflow-hidden rounded-osce-lg border border-border">
              <ul className="divide-y divide-border">
                {shown.map((claim) => (
                  <ClaimRow
                    key={`${tab}-${claim.id}`}
                    claim={claim}
                    defaultOpen={tab === "resolve"}
                    rulings={ruling}
                  />
                ))}
              </ul>
            </div>
          ) : (
            <p className="py-8 text-center text-osce-meta text-ink-subtle">
              {TABS.find((entry) => entry.id === tab)?.empty}
            </p>
          )}
        </>
      ) : facts ? (
        <p className="py-8 text-center text-osce-meta text-ink-subtle">
          {progress
            ? "Claims found. The first verdicts arrive in about half a minute."
            : "No claim here could be checked against a guideline."}
        </p>
      ) : null}
    </div>
  );
}
