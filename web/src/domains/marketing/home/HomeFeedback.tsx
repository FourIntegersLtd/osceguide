"use client";

import { useState } from "react";
import { sendSiteMessage } from "@/capabilities/help/api";
import { errorMessage } from "@/foundation/hooks";
import { useToast } from "@/foundation/hooks/useToast";
import { SiteButton } from "@/foundation/ui";
import { SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

type Panel = "truth" | "wish";

type PanelDef = { id: Panel; tab: string; label: string; aside: string; prefix: string };

const TRUTH: PanelDef = { id: "truth", tab: "Harsh Truth", label: "Tell us what you really think about our product", aside: "(We promise we can take it…)", prefix: "Harsh truth" };
const WISH: PanelDef = { id: "wish", tab: "Feature Wishlist", label: "Got a feature you wish existed? Share it with us!", aside: "No idea is too wild.", prefix: "Feature wishlist" };
const PANELS = [TRUTH, WISH];

const FIELD = "mt-3 block min-h-36 w-full rounded-xl border border-site-rule bg-site-card p-4 text-site-ink placeholder:text-site-faint focus-visible:outline focus-visible:outline-2 focus-visible:outline-site-brand";

/** "Help us improve": files one `product_feedback` message carrying whichever boxes were filled. */
export function HomeFeedback() {
  const toast = useToast();
  const [panel, setPanel] = useState<Panel>("truth");
  const [text, setText] = useState<Record<Panel, string>>({ truth: "", wish: "" });
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const parts = PANELS.filter((p) => text[p.id].trim()).map((p) => `${p.prefix}:\n${text[p.id].trim()}`);
    if (parts.length === 0) return;
    setBusy(true);
    try {
      await sendSiteMessage({ kind: "product_feedback", body: parts.join("\n\n"), source: "landing/help-us-improve" });
      setText({ truth: "", wish: "" });
      setSent(true);
    } catch (err) {
      toast.error("We couldn't send your feedback", errorMessage(err) || "Please try again in a moment.");
    } finally {
      setBusy(false);
    }
  }

  const current = panel === "truth" ? TRUTH : WISH;

  return (
    <Section id="feedback" tone="pale">
      <SectionHead title="Your feedback shapes our platform. Be honest, be bold!" />
      <form onSubmit={submit} className="mx-auto mt-10 max-w-2xl rounded-2xl border border-site-line bg-site-card p-5 text-left sm:p-8">
        <div role="tablist" aria-label="Kind of feedback" className="flex rounded-full bg-site-pale p-1">
          {PANELS.map((p) => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={panel === p.id}
              onClick={() => setPanel(p.id)}
              className={`h-10 flex-1 rounded-full px-3 text-sm font-semibold transition-colors ${
                panel === p.id ? "bg-site-card text-site-brand shadow-sm" : "text-site-muted hover:text-site-ink"
              }`}
            >
              {p.tab}
            </button>
          ))}
        </div>
        <label className="mt-6 block font-semibold text-site-ink">
          {current.label} <span className="font-normal text-site-muted">{current.aside}</span>
          <textarea
            name={current.id}
            value={text[current.id]}
            onChange={(e) => setText((t) => ({ ...t, [current.id]: e.target.value }))}
            className={FIELD}
          />
        </label>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <SiteButton type="submit" disabled={busy} size="lg">
            {busy ? "Sending…" : "Submit feedback"}
          </SiteButton>
          <p role="status" aria-live="polite" className="text-sm text-site-body">
            {sent ? "Thank you for your feedback. Your insights help us improve." : ""}
          </p>
        </div>
      </form>
    </Section>
  );
}
