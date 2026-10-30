import { FiBarChart2, FiBookOpen, FiMic } from "react-icons/fi";
import { AthenaAvatar } from "@/foundation/ui";
import { CardGrid } from "@/domains/marketing/home/Blocks";
import { Section } from "@/domains/marketing/home/Section";

const STEPS = [
  { label: "01 · CHOOSE", Icon: FiBookOpen, title: "Choose the number of stations" },
  { label: "02 · CONSULT", Icon: FiMic, title: "Speak to an AI patient that responds like a real human" },
  { label: "03 · IMPROVE", Icon: FiBarChart2, title: "Get structured feedback and a debrief with our custom AI tutor, Athena", aside: <AthenaAvatar className="h-11 w-11" /> },
];

export function HomeSteps() {
  return (
    <Section label="How it works">
      <CardGrid items={STEPS} />
    </Section>
  );
}
