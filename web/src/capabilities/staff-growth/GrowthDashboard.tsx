"use client";

import { useState } from "react";
import { LuTrendingUp } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  Button,
  Card,
  Input,
} from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import {
  PlatformFilterBar,
  PlatformFilterSearch,
} from "@/domains/platform/PlatformFilterBar";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  addPartnerReporter,
  listPartnerRefIds,
  readPartnerFunnel,
  type FunnelRead,
} from "@/capabilities/staff-growth/api";

const DEFAULT_PARTNER = "bmj";

export function GrowthDashboard() {
  const [partner, setPartner] = useState(DEFAULT_PARTNER);
  const [reporterEmail, setReporterEmail] = useState("");
  const [reporterBusy, setReporterBusy] = useState(false);
  const [reporterError, setReporterError] = useState<string | null>(null);
  const toast = useToast();

  const funnel = useAsync((signal) => readPartnerFunnel(partner, signal), [partner]);
  const refs = useAsync((signal) => listPartnerRefIds(partner, signal), [partner]);

  const addReporter = async () => {
    if (!reporterEmail.trim()) return;
    setReporterBusy(true);
    setReporterError(null);
    try {
      await addPartnerReporter(partner, reporterEmail.trim());
      setReporterEmail("");
      toast.success("Reporter added");
    } catch (cause) {
      setReporterError(errorMessage(cause));
    } finally {
      setReporterBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <PlatformPageHeader
        title="Growth"
        description="Partner attribution funnel, tracking links and reporter access."
        icon={LuTrendingUp}
      />

      <PlatformFilterBar>
        <PlatformFilterSearch
          value={partner}
          onChange={setPartner}
          placeholder="Partner slug (e.g. bmj)"
          aria-label="Partner slug"
        />
      </PlatformFilterBar>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink">Funnel</h2>
        <AsyncBoundary state={funnel}>
          {(data) => <FunnelCard funnel={data} />}
        </AsyncBoundary>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink">Tracking references</h2>
        <AsyncBoundary
          state={refs}
          isEmpty={(page) => page.items.length === 0}
          empty={{ title: "No ref ids", description: "This partner has no tracking links yet." }}
        >
          {(page) => (
            <Card>
              <ul className="divide-y divide-border">
                {page.items.map((ref) => (
                  <li key={ref.ref_id} className="px-5 py-3">
                    <p className="truncate text-sm font-medium text-ink">{ref.ref_id}</p>
                    <p className="truncate text-xs text-ink-subtle">
                      {ref.exam_code} · {ref.landing_path}
                    </p>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </AsyncBoundary>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink">Reporters</h2>
        <Card padding="md">
          <div className="flex max-w-md flex-col gap-3">
            {reporterError ? <Alert tone="danger">{reporterError}</Alert> : null}
            <Input
              type="email"
              label="Reporter email"
              value={reporterEmail}
              onChange={(e) => setReporterEmail(e.target.value)}
            />
            <Button disabled={reporterBusy || !reporterEmail.trim()} onClick={() => void addReporter()}>
              {reporterBusy ? "Adding…" : "Add reporter"}
            </Button>
          </div>
        </Card>
      </section>
    </div>
  );
}

function FunnelCard({ funnel }: { funnel: FunnelRead }) {
  const rows = [
    { label: "Arrivals", value: funnel.arrivals },
    { label: "Signups", value: funnel.signups },
    { label: "Signup rate", value: `${Math.round(funnel.signup_rate * 100)}%` },
    { label: "Purchases", value: funnel.purchases },
    { label: "Purchase rate", value: `${Math.round(funnel.purchase_rate * 100)}%` },
  ];

  return (
    <Card padding="md">
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((row) => (
          <li key={row.label} className="rounded-control border border-border px-4 py-3">
            <p className="text-xs text-ink-subtle">{row.label}</p>
            <p className="text-lg font-semibold text-ink">{row.value}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
