import type { ReactNode } from "react";

/* Section heading, mono eyebrow and icon tile on the `.site-root` tokens. */
export function SectionHead({ title, sub, eyebrow, onNavy = false, center = true, as: Title = "h2" }: { title: ReactNode; sub?: string; eyebrow?: string; onNavy?: boolean; center?: boolean; as?: "h1" | "h2" }) {
  return (
    <div className={center ? "mx-auto max-w-3xl text-center" : "max-w-2xl"}>
      {eyebrow && (
        <div className="mb-4">
          <Eyebrow onNavy={onNavy}>{eyebrow}</Eyebrow>
        </div>
      )}
      <Title className={`font-landing-heading text-3xl font-bold leading-tight tracking-tight sm:text-4xl ${onNavy ? "text-white" : "text-site-ink"}`}>{title}</Title>
      {sub && <p className={`mt-4 text-lg leading-relaxed ${onNavy ? "text-site-on-navy" : "text-site-body"}`}>{sub}</p>}
    </div>
  );
}

export function Eyebrow({ children, onNavy = false }: { children: ReactNode; onNavy?: boolean }) {
  return (
    <span className={`font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] ${onNavy ? "text-site-on-navy-dim" : "text-site-brand"}`}>{children}</span>
  );
}

/** The rounded square that holds a section's icon. */
export function IconTile({ children, onNavy = false }: { children: ReactNode; onNavy?: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xl ${onNavy ? "bg-white/10 text-white" : "bg-site-pale text-site-brand"}`}
    >
      {children}
    </span>
  );
}
