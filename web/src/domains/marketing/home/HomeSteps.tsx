import Image from "next/image";
import { FiBarChart2, FiBookOpen, FiMic } from "react-icons/fi";
import { ATHENA_IMAGE_SRC } from "@/foundation/ui/AthenaIdentity";
import { IconTile } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

const STEPS = [
  { n: "01 · CHOOSE", Icon: FiBookOpen, title: "Pick your exam and a station", body: "SCA, PLAB 2, CASC or Orthopaedic ST3. Read the candidate notes under a reading timer." },
  { n: "02 · CONSULT", Icon: FiMic, title: "Talk to your AI patient", body: "A realistic voice patient answers, hesitates and worries, on the exam clock." },
  { n: "03 · IMPROVE", Icon: FiBarChart2, title: "Get marked, then debrief", body: "Domain feedback with the moment each mark was decided, then a walkthrough with Athena." },
] as const;

export function HomeSteps() {
  return (
    <Section label="How it works">
      <div className="grid gap-5 md:grid-cols-3">
        {STEPS.map(({ n, Icon, title, body }, i) => (
          <div key={n} className="rounded-2xl border border-site-line bg-site-card p-6">
            <IconTile>
              <Icon />
            </IconTile>
            <b className="mt-4 block font-landing-mono text-[11px] font-medium tracking-[0.13em] text-site-brand">{n}</b>
            <h3 className="mt-2 flex items-center gap-2.5 font-landing-heading text-xl font-bold text-site-ink">
              {title}
              {i === 2 && <Image src={ATHENA_IMAGE_SRC} alt="Athena" width={44} height={44} className="h-11 w-11 shrink-0 rounded-full object-cover" />}
            </h3>
            <p className="mt-2 text-site-body">{body}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}
