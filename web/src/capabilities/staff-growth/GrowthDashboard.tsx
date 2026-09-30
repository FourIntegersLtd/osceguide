"use client";

import { useState } from "react";
import { LuTrendingUp } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  Button,
  Input,
  PlatformPageHeader,
  PlatformFilterBar,
  PlatformFilterSearch,
  Panel,
} from "@/foundation/ui";
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

      <Panel title="Funnel" padding="none">
        <AsyncBoundary state={funnel}>
          {(data) => <FunnelCard funnel={data} />}
        </AsyncBoundary>
      </Panel>

      <Panel title="Tracking references" padding="none">
        <AsyncBoundary
          state={refs}
          isEmpty={(page) => page.items.length === 0}
          empty={{ title: "No ref ids", description: "This partner has no tracking links yet." }}
        >
          {(page) => (
          <ul className="divide-y divide-border">
              {page.items.map((ref) => (
                <li key={ref.ref_id} className="px-5 py-3">
                  <p className="truncate text-osce-data font-medium text-ink">{ref.ref_id}</p>
                  <p className="truncate text-osce-caption text-ink-subtle">
                    {ref.exam_code} · {ref.landing_path}
                  </p>
                </li>
              ))}
              </ul>
          )}
        </AsyncBoundary>
      </Panel>

      <Panel title="Reporters" padding="none">
        <div className="flex max-w-md flex-col gap-3 p-5">
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
      </Panel>
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
    <ul className="grid p-5 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {rows.map((row) => (
          <li key={row.label} className="rounded-osce-md border border-border px-4 py-3">
            <p className="text-osce-caption text-ink-subtle">{row.label}</p>
            <p className="text-osce-subheading font-semibold text-ink">{row.value}</p>
          </li>
        ))}
      </ul>
  );
}
