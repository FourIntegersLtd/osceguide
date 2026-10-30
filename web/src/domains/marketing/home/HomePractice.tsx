import type { IconType } from "react-icons";
import { FiCalendar, FiClock, FiSliders, FiZap } from "react-icons/fi";
import { LandingDemoVideo } from "@/domains/marketing/LandingDemoVideo";
import { Eyebrow, IconTile, SectionHead } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";

const MARKETPLACE_VIDEO_SRC =
  "https://osceguide.s3.eu-west-2.amazonaws.com/Four+Integers+Ltd/osceguide-marketplace-how-it-works.mp4";

type PracticeItem = { Icon: IconType; title: string; body: string };

const TRIO: readonly PracticeItem[] = [
  { Icon: FiZap, title: "Live Practice", body: "Get matched instantly with available colleagues and start practising immediately." },
  { Icon: FiCalendar, title: "Marketplace", body: "Post your availability or browse sessions from colleagues. Schedule at times that work for both of you." },
  { Icon: FiClock, title: "Automatic Timing", body: "Built-in timer matches the exam format. Practise with realistic time constraints." },
];

type HomePracticeProps = {
  eyebrow?: string;
  title?: string;
  sub?: string;
};

export function HomePractice({
  eyebrow = "Practice with colleagues",
  title = "Practise with a real person, on your schedule",
  sub = "Choose between instant matching or scheduled sessions and practise in real-time video consultations.",
}: HomePracticeProps) {
  return (
    <Section id="practice" tone="pale">
      <div className="grid items-center gap-12 lg:grid-cols-2">
        <div>
          {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
          <h2 className="mt-3 font-landing-heading text-3xl font-bold leading-tight text-site-ink sm:text-4xl">{title}</h2>
          <p className="mt-4 text-lg text-site-body">{sub}</p>
          <div className="mt-8 space-y-6">
            {TRIO.map(({ Icon, title, body }) => (
              <div key={title} className="flex gap-4">
                <IconTile><Icon /></IconTile>
                <div>
                  <h3 className="font-landing-heading text-lg font-bold text-site-ink">{title}</h3>
                  <p className="text-site-body">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <LandingDemoVideo src={MARKETPLACE_VIDEO_SRC} title="How the OSCE Guide marketplace works" />
      </div>
    </Section>
  );
}

export function HomeNeurodiversity() {
  return (
    <Section tone="navy">
      <SectionHead
        onNavy
        title="We support our neurodiverse colleagues"
        sub="OSCE Guide is built to be inclusive. If you need extra time for your learning, we have you covered. No questions asked."
      />
      <div className="mt-12 grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-white/15 bg-white/5 p-6">
          <IconTile onNavy><FiClock /></IconTile>
          <h3 className="mt-4 font-landing-heading text-xl font-bold text-white">Extra time when you need it</h3>
          <p className="mt-2 text-site-on-navy">
            Turn on Extra Time in your Profile if you need additional time to support your neurodiverse learning needs. Your practice will use your chosen durations for every station.
          </p>
          <div aria-hidden="true" className="mt-5 flex items-center justify-between rounded-lg bg-white/10 px-4 py-3 text-sm text-white">
            Extra Time
            <span className="relative h-6 w-11 rounded-full bg-site-pale-strong"><i className="absolute right-0.5 top-0.5 h-5 w-5 rounded-full bg-site-navy" /></span>
          </div>
        </div>
        <div className="rounded-2xl border border-white/15 bg-white/5 p-6">
          <IconTile onNavy><FiSliders /></IconTile>
          <h3 className="mt-4 font-landing-heading text-xl font-bold text-white">Your reading and simulation timers</h3>
          <p className="mt-2 text-site-on-navy">
            Configure your own reading and simulation timers so practice matches your exam arrangements or how you learn best.
          </p>
          <div aria-hidden="true" className="mt-5 grid grid-cols-2 gap-3 text-sm text-site-on-navy">
            <div className="rounded-lg bg-white/10 px-4 py-3"><b className="block font-landing-mono text-2xl text-white">03:00</b>Reading</div>
            <div className="rounded-lg bg-white/10 px-4 py-3"><b className="block font-landing-mono text-2xl text-white">15:00</b>Simulation</div>
          </div>
        </div>
      </div>
    </Section>
  );
}
