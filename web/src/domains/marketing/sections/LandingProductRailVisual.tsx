"use client";

import Image from "next/image";
import { ATHENA_IMAGE_SRC } from "@/foundation/ui/AthenaIdentity";
import type { LandingProductRailItem } from "./landingProductRailContent";

const WAVEFORM_DELAYS = ["0s", "0.1s", "0.2s", "0.3s"];

function MiniWaveform() {
  return (
    <div className="flex h-3.5 items-center gap-[3px]" aria-hidden>
      {WAVEFORM_DELAYS.map((delay) => (
        <span
          key={delay}
          className="voice-memo-bar h-full w-[2.5px] rounded-sm bg-osce-accent"
          style={{ animationDelay: delay }}
        />
      ))}
    </div>
  );
}

function RailCardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-[186px] bg-[linear-gradient(160deg,#EAF0F8,#F7F8FA)] p-[18px]">
      <div className="rounded-[9px] border border-b2c-border bg-white p-3.5 shadow-[0_4px_14px_rgba(16,24,40,0.06)]">
        {children}
      </div>
    </div>
  );
}

export function LandingProductRailVisual({
  item,
}: {
  item: LandingProductRailItem;
}) {
  if (item.visual === "voice") {
    return (
      <RailCardShell>
        <p className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.1em] text-[#8A94A6]">
          Live station
        </p>
        <p className="mt-2 font-landing-body text-[13px] leading-snug text-osce-ink-900">
          &ldquo;My eyes have gone yellow.&rdquo;
        </p>
        <div className="mt-3 flex items-center gap-2.5">
          <MiniWaveform />
          <span className="font-landing-mono text-[11px] text-b2c-text-secondary">
            07:12 left
          </span>
        </div>
      </RailCardShell>
    );
  }

  if (item.visual === "marketplace") {
    return (
      <div className="h-[186px] bg-[linear-gradient(160deg,#F3EFF1,#F7F8FA)] p-[18px]">
        <div className="rounded-[9px] border border-b2c-border bg-white p-3.5 shadow-[0_4px_14px_rgba(16,24,40,0.06)]">
          <p className="font-landing-mono text-[10px] font-medium uppercase tracking-[0.1em] text-[#8A94A6]">
            SCA practise session
          </p>
          <div className="mt-2.5 grid grid-cols-7 gap-1">
            {["#F2F4F7", "#F2F4F7", "#EAF0F8", "#3A5D8F", "#F2F4F7", "#EAF0F8", "#F2F4F7"].map(
              (color, index) => (
                <div
                  key={index}
                  className="h-[18px] rounded-[3px]"
                  style={{ backgroundColor: color }}
                />
              ),
            )}
          </div>
          <p className="mt-3 font-landing-body text-xs leading-snug text-landing-ink-body">
            Thu 19:30 · Dr M. is free to play the patient
          </p>
        </div>
      </div>
    );
  }

  if (item.visual === "feedback") {
    const bars = [
      { label: "Data gathering", value: "7/9", width: "78%", color: "#2F6E52" },
      { label: "Management", value: "5/9", width: "55%", color: "#8A6320" },
      { label: "Relating to others", value: "3/9", width: "33%", color: "#9E3B36" },
    ];

    return (
      <RailCardShell>
        <div className="flex flex-col gap-3">
          {bars.map((bar) => (
            <div key={bar.label}>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="font-landing-body text-xs font-medium text-osce-ink-900">
                  {bar.label}
                </span>
                <span className="font-landing-mono text-[11px] text-b2c-text-secondary">
                  {bar.value}
                </span>
              </div>
              <div className="h-[5px] overflow-hidden rounded-[3px] bg-b2c-border-light">
                <div
                  className="h-full"
                  style={{ width: bar.width, backgroundColor: bar.color }}
                />
              </div>
            </div>
          ))}
        </div>
      </RailCardShell>
    );
  }

  return (
    <div className="h-[186px] bg-[linear-gradient(160deg,#F1F2F0,#F7F8FA)] p-[18px]">
      <div className="rounded-[9px] border border-b2c-border bg-white p-3.5 shadow-[0_4px_14px_rgba(16,24,40,0.06)]">
        <div className="flex items-start gap-2.5">
          <Image
            src={ATHENA_IMAGE_SRC}
            alt="Athena"
            width={32}
            height={32}
            className="h-8 w-8 shrink-0 rounded-full border border-[#D0D5DD] object-cover object-[50%_18%]"
          />
          <div>
            <p className="font-landing-body text-xs font-medium text-osce-ink-900">
              Athena
            </p>
            <p className="mt-1 font-landing-body text-xs leading-snug text-landing-ink-body">
              Let&apos;s start with the cue you missed twice.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
