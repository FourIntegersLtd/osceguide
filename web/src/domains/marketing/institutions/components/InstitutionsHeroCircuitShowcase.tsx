const WAVEFORM_DELAYS = ["0s", "0.08s", "0.16s", "0.24s", "0.32s"];

type CircuitStatus = "complete" | "live" | "upnext" | "waiting";

const CIRCUIT_ROWS: Array<{
  station: string;
  candidate: string;
  status: CircuitStatus;
}> = [
  { station: "Chest pain", candidate: "AM", status: "complete" },
  { station: "Low mood", candidate: "SR", status: "live" },
  { station: "Diabetes review", candidate: "-", status: "upnext" },
  { station: "Abdominal pain", candidate: "PK", status: "waiting" },
];

function Eyebrow({ children }: { children: string }) {
  return (
    <div className="font-landing-mono text-[8px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted sm:text-[10px]">
      {children}
    </div>
  );
}

function MiniWaveform() {
  return (
    <div className="flex h-3 items-center gap-[2px]" aria-hidden>
      {WAVEFORM_DELAYS.map((delay) => (
        <span
          key={delay}
          className="voice-memo-bar h-full w-[2px] rounded-sm bg-osce-accent"
          style={{ animationDelay: delay }}
        />
      ))}
    </div>
  );
}

function StatusPill({ status }: { status: CircuitStatus }) {
  if (status === "complete") {
    return (
      <span className="inline-flex items-center rounded-md border border-osce-band-competentBorder bg-osce-band-competentBg px-2 py-0.5 font-landing-mono text-[9px] font-medium uppercase tracking-[0.08em] text-osce-band-competent sm:text-[10px]">
        Complete
      </span>
    );
  }
  if (status === "live") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md border border-osce-accent-subtle bg-osce-accent-muted px-2 py-0.5 font-landing-mono text-[9px] font-medium uppercase tracking-[0.08em] text-osce-accent sm:text-[10px]">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-osce-accent opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-osce-accent" />
        </span>
        Live
      </span>
    );
  }
  if (status === "upnext") {
    return (
      <span className="inline-flex items-center rounded-md border border-b2c-border bg-b2c-surface-muted px-2 py-0.5 font-landing-mono text-[9px] font-medium uppercase tracking-[0.08em] text-b2c-text-secondary sm:text-[10px]">
        Up next
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-md border border-b2c-border-light px-2 py-0.5 font-landing-mono text-[9px] font-medium uppercase tracking-[0.08em] text-b2c-text-muted sm:text-[10px]">
      Waiting
    </span>
  );
}

export function InstitutionsHeroCircuitShowcase() {
  return (
    <div
      className="relative mx-auto w-full min-h-[380px] max-w-[1000px] px-1 pb-6 sm:min-h-[420px] sm:px-0 sm:pb-0"
      aria-hidden
    >
      {/* Back-left: active consultation */}
      <div
        className="pointer-events-none absolute bottom-6 left-[1%] top-2 w-[56%] rounded-[var(--landing-radius-card,0.5rem)] border border-landing-warm-strong bg-landing-card p-3 shadow-landing-showcase-side rotate-[-8deg] sm:bottom-auto sm:left-[6%] sm:top-10 sm:h-[360px] sm:w-[50%] sm:max-w-[400px] sm:p-6 sm:rotate-[-9deg] lg:left-[4%] lg:top-[70px] lg:p-7"
      >
        <Eyebrow>Live station</Eyebrow>
        <div className="mt-2 font-landing-heading text-base font-semibold leading-tight tracking-[-0.025em] text-osce-ink-900 sm:mt-3 sm:text-[22px]">
          Low mood
        </div>
        <p className="mt-1 font-landing-body text-[11px] leading-snug text-b2c-text-muted sm:mt-2 sm:text-sm">
          34F · virtual patient
        </p>
        <p className="mt-4 font-landing-body text-[11px] italic leading-relaxed text-landing-ink-body sm:mt-6 sm:text-[13px]">
          &ldquo;I&apos;ve been feeling really down lately.&rdquo;
        </p>
        <div className="mt-4 flex items-center gap-2.5 sm:mt-6">
          <MiniWaveform />
          <span className="font-landing-mono text-[10px] tabular-nums text-b2c-text-secondary sm:text-[11px]">
            04:32 left
          </span>
        </div>
      </div>

      {/* Back-right: cohort progress */}
      <div
        className="pointer-events-none absolute bottom-6 right-[1%] top-1 flex w-[53%] flex-col justify-between rounded-[var(--landing-radius-card,0.5rem)] border border-landing-warm-strong bg-landing-card p-3 shadow-landing-showcase-side rotate-[8deg] sm:bottom-auto sm:right-[6%] sm:top-8 sm:h-[380px] sm:w-[48%] sm:max-w-[380px] sm:p-6 sm:rotate-[8deg] lg:right-[4%] lg:top-14 lg:p-7"
      >
        <div>
          <Eyebrow>Cohort progress</Eyebrow>
          <div className="mt-2 text-right font-landing-heading text-xl font-medium leading-[1.1] text-osce-ink-900 sm:mt-3 sm:text-[30px]">
            18 / 24
          </div>
          <p className="mt-1 text-right font-landing-body text-[11px] text-b2c-text-muted sm:text-sm">
            Candidates complete
          </p>
        </div>
        <div className="sm:mt-auto">
          <div className="mb-2 flex items-end justify-between gap-2">
            <Eyebrow>Session</Eyebrow>
            <span className="font-landing-mono text-[10px] tabular-nums text-b2c-text-secondary">
              75%
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-landing-hairline">
            <div className="h-full w-3/4 rounded-full bg-osce-accent" />
          </div>
        </div>
      </div>

      {/* Front: supervisor circuit view */}
      <div className="relative z-10 mx-auto w-[84%] max-w-[840px] overflow-hidden rounded-[var(--landing-radius-panel,10px)] border border-landing-warm bg-landing-card text-left shadow-landing-showcase sm:w-[90%] md:w-full">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-landing-hairline px-3 py-3 sm:px-8 sm:py-5">
          <div>
            <Eyebrow>Circuit live</Eyebrow>
            <div className="mt-1 font-landing-heading text-[15px] font-semibold leading-tight tracking-[-0.02em] text-osce-ink-900 sm:mt-1.5 sm:text-[clamp(1.125rem,2vw,1.375rem)]">
              Medical School · Skills Week
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-osce-band-competentBorder bg-osce-band-competentBg px-2.5 py-1 font-landing-mono text-[9px] font-medium uppercase tracking-[0.08em] text-osce-band-competent sm:text-[10px]">
            <span className="h-1.5 w-1.5 rounded-full bg-osce-band-competent" />
            6 stations
          </span>
        </div>

        <div className="hidden items-center gap-3 border-b border-landing-hairline px-8 py-2.5 sm:flex">
          <div className="flex-[1.4] font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
            Station
          </div>
          <div className="w-16 shrink-0 font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
            Candidate
          </div>
          <div className="w-[88px] shrink-0 text-right font-landing-mono text-[10px] font-medium uppercase tracking-[0.14em] text-b2c-text-muted">
            Status
          </div>
        </div>

        <div className="divide-y divide-landing-hairline">
          {CIRCUIT_ROWS.map((row) => (
            <div
              key={row.station}
              className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2.5 sm:gap-3 sm:px-8 sm:py-3.5"
            >
              <div className="min-w-0 flex-[1.4] font-landing-body text-[12px] font-medium text-osce-ink-900 sm:text-sm">
                {row.station}
              </div>
              <div className="w-16 shrink-0 font-landing-mono text-[11px] tabular-nums text-b2c-text-secondary sm:text-xs">
                {row.candidate}
              </div>
              <div className="ml-auto w-[88px] shrink-0 text-right sm:ml-0">
                {row.status === "live" ? (
                  <div className="flex items-center justify-end gap-2">
                    <MiniWaveform />
                    <StatusPill status={row.status} />
                  </div>
                ) : (
                  <StatusPill status={row.status} />
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-landing-hairline bg-landing-card-muted px-3 py-2.5 sm:px-8 sm:py-3.5">
          <span className="font-landing-body text-[11px] text-b2c-text-secondary sm:text-sm">
            Supervisor view · Faculty can observe without interrupting
          </span>
          <span className="font-landing-mono text-[10px] tabular-nums text-b2c-text-muted">
            Station 2 of 6
          </span>
        </div>
      </div>
    </div>
  );
}
