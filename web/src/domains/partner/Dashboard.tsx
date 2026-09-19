"use client";

import { LuArrowRight, LuTrendingUp, LuUserPlus, LuUsers } from "react-icons/lu";
import { AsyncBoundary, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readFunnel, type PartnerFunnel } from "@/domains/partner/api";

/**
 * How a partner's audience is arriving.
 *
 * A partner does not examine a cohort, so a results dashboard would say
 * nothing. What they ask is whether the people they sent us signed up and
 * bought, which is what `growth/partners/{partner}/funnel` answers in one
 * request.
 */
export function PartnerDashboard({ partner }: { partner: string }) {
  const state = useAsync((signal) => readFunnel(partner, signal), [partner]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Overview"
        description="How the people you sent us are progressing."
      />
      <AsyncBoundary state={state}>{(data) => <Funnel data={data} />}</AsyncBoundary>
    </div>
  );
}

function Funnel({ data }: { data: PartnerFunnel }) {
  const { hrefFor } = useSurface();

  return (
    <div className="flex flex-col gap-4">
      <section className="grid gap-3 sm:grid-cols-3">
        <Stat icon={LuUsers} label="Arrivals" value={data.arrivals} />
        <Stat
          icon={LuUserPlus}
          label="Signed up"
          value={data.signups}
          rate={data.signup_rate}
          of="of arrivals"
        />
        <Stat
          icon={LuTrendingUp}
          label="Purchased"
          value={data.purchases}
          rate={data.purchase_rate}
          of="of signups"
        />
      </section>

      <Card title="Tracking references">
        <p className="text-sm text-ink-muted">
          Every link you publish carries a reference, and each one is counted separately.
        </p>
        <a
          href={hrefFor("/reporting")}
          className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
        >
          See them all <LuArrowRight className="h-4 w-4" aria-hidden />
        </a>
      </Card>
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  rate,
  of,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  rate?: number;
  of?: string;
}) {
  return (
    <Card>
      <Icon className="h-4 w-4 text-ink-subtle" aria-hidden />
      <p className="mt-2 text-2xl font-semibold text-ink">{value.toLocaleString()}</p>
      <p className="text-sm text-ink-muted">{label}</p>
      {rate !== undefined && (
        // A rate with no denominator named is a number people misread as a
        // share of everything.
        <p className="mt-1 text-xs text-ink-subtle">
          {(rate * 100).toFixed(1)}% {of}
        </p>
      )}
    </Card>
  );
}
