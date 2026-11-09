import { Eyebrow } from "@/foundation/ui";
import { Section } from "@/domains/marketing/home/Section";
import { FOUNDERS_LETTER } from "@/domains/marketing/foundersLetter";
import { FOUNDERS } from "@/domains/marketing/landingCopy";

/** A short note, narrow and left-aligned: not a card. */
export function FoundersNote() {
  return (
    <Section tone="ground" label="From the founders">
      <div className="max-w-2xl">
        <Eyebrow>{FOUNDERS.eyebrow}</Eyebrow>
        <div className="mt-5 space-y-4 text-[17px] leading-[1.7] text-site-body">
          {FOUNDERS_LETTER.map((text) => (
            <p key={text}>{text}</p>
          ))}
        </div>
        <p className="mt-6"><b className="text-site-ink">{FOUNDERS.signoff.names}</b>, <span className="text-site-muted">{FOUNDERS.signoff.role}</span></p>
      </div>
    </Section>
  );
}
