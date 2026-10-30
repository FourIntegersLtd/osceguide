import { FiBarChart2, FiBookOpen, FiMic } from "react-icons/fi";
import { AthenaAvatar, IconTile } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

const STEPS = [
  { n: "01 · CHOOSE", Icon: FiBookOpen, title: "Choose the number of stations" },
  { n: "02 · CONSULT", Icon: FiMic, title: "Speak to an AI patient that responds like a real human" },
  { n: "03 · IMPROVE", Icon: FiBarChart2, title: "Get structured feedback and a debrief with our custom AI tutor, Athena" },
] as const;

export function HomeSteps() {
  return (
    <Section label="How it works">
      <div className="grid gap-5 md:grid-cols-3">
        {STEPS.map(({ n, Icon, title }, i) => (
          <div key={n} className="flex h-full min-w-0 flex-col rounded-2xl border border-site-line bg-site-card p-6">
            <div className="flex items-center justify-between gap-3">
              <IconTile>
                <Icon />
              </IconTile>
              {i === 2 && <AthenaAvatar className="h-11 w-11" />}
            </div>
            <b className="mt-4 block font-landing-mono text-[11px] font-medium tracking-[0.13em] text-site-brand">{n}</b>
            <h3 className="mt-2 text-balance break-words font-landing-heading text-xl font-bold leading-snug text-site-ink">{title}</h3>
          </div>
        ))}
      </div>
    </Section>
  );
}
