"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { LuArrowRight, LuBuilding2, LuGraduationCap, LuBriefcase } from "react-icons/lu";
import { ButtonLink, Spinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session";

/**
 * The public front door.
 *
 * Deliberately outside every surface: a visitor has no arm yet, and the three
 * described below are the same product seen from three sides rather than three
 * things to choose between. Somebody already signed in never sees this.
 */
export default function LandingPage() {
  const { status, ready, session } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!ready || status !== "authenticated") return;
    // Where you land is decided by what you belong to, not by which link you
    // followed — one identity, several workspaces.
    const memberships = session?.user.memberships ?? [];
    if (memberships.length === 1 && memberships[0]) {
      router.replace(`/assess/${memberships[0].org_slug}`);
    } else if (memberships.length > 1) {
      router.replace("/assess");
    } else {
      router.replace("/practice");
    }
  }, [ready, status, session, router]);

  if (!ready || status === "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Spinner label="Loading" />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-canvas">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-5">
        <span className="text-sm font-semibold tracking-tight text-ink">OSCE Guide</span>
        <nav className="flex items-center gap-2">
          <Link href="/login" className="rounded-control px-3 py-2 text-sm text-ink-muted hover:text-ink">
            Sign in
          </Link>
          <ButtonLink size="sm" href="/register">
            Get started
          </ButtonLink>
        </nav>
      </header>

      <section className="mx-auto w-full max-w-3xl px-4 py-16 text-center sm:py-24">
        <h1 className="text-balance text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
          Clinical consultations you can actually practise
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-pretty text-base leading-7 text-ink-muted">
          Speak to a simulated patient, get marked against the real framework, and read feedback
          that tells you what to do differently. On your own, or run as an examination by your
          institution.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <ButtonLink size="lg" href="/register">
            Start practising <LuArrowRight className="h-4 w-4" aria-hidden />
          </ButtonLink>
          <ButtonLink size="lg" variant="secondary" href="/login">
            Sign in
          </ButtonLink>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-5xl gap-4 px-4 pb-24 sm:grid-cols-3">
        <Arm
          icon={LuGraduationCap}
          title="Practise"
          body="Build a mock from the station library and work through it. Every attempt is marked against the same framework your exam uses."
        />
        <Arm
          icon={LuBuilding2}
          title="Examine"
          body="Run circuits for your cohort, watch them live, mark alongside the machine, and release results when they are signed off."
        />
        <Arm
          icon={LuBriefcase}
          title="Hire"
          body="Assess candidates against the same scenarios, in exam mode, with a record you can defend months later."
        />
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto w-full max-w-5xl px-4 py-8 text-sm text-ink-subtle">
          © {new Date().getFullYear()} OSCE Guide
        </div>
      </footer>
    </main>
  );
}

function Arm({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-panel border border-border bg-surface p-5">
      <Icon className="h-5 w-5 text-accent" aria-hidden />
      <h2 className="mt-3 text-sm font-semibold text-ink">{title}</h2>
      <p className="mt-1.5 text-sm leading-6 text-ink-muted">{body}</p>
    </div>
  );
}
