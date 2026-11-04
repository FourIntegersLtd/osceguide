"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, B2CPageHeader, Button, ButtonLink, Input, Spinner, Panel } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createSitting, listProgrammes, type Programme, type SittingMode } from "@/domains/assess/api";
import { readAllCohorts, type Cohort } from "@/domains/assess/roster/api";
import { CohortField, ModeField, ProgrammeField, ScheduledForField } from "@/domains/assess/SittingFields";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/** Schedule a sitting against a programme (exam + published rubric). */
export function NewSitting({ orgSlug }: { orgSlug: string }) {
  const w = useAssessWords();
  const router = useRouter();
  const { hrefFor } = useSurface();

  const programmes = useAsync(
    async (signal) => ({
      programmes: (await listProgrammes(orgSlug, signal)).items,
      cohorts: await readAllCohorts(orgSlug, signal),
    }),
    [orgSlug],
  );

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        back={{ href: hrefFor("/sittings"), label: w.Sittings }}
        title={w.scheduleSitting}
        subtitle={`A training ${w.sitting} rotates a group through stations; an exam ${w.sitting} is one ${w.trainee}, marked, signed off and released. Add circuits next.`}
      />
      <AsyncBoundary state={programmes}>
        {(loaded) => (
          <Form
            orgSlug={orgSlug}
            programmes={loaded.programmes}
            cohorts={loaded.cohorts}
            programmesHref={hrefFor("/programmes")}
            cancelHref={hrefFor("/sittings")}
            onCreated={(id) => router.push(hrefFor(`/sittings/${id}`))}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Form({
  orgSlug,
  programmes,
  cohorts,
  programmesHref,
  cancelHref,
  onCreated,
}: {
  orgSlug: string;
  programmes: Programme[];
  cohorts: Cohort[];
  programmesHref: string;
  cancelHref: string;
  onCreated: (sittingId: string) => void;
}) {
  const w = useAssessWords();
  const activeProgrammes = useMemo(
    () => programmes.filter((programme) => programme.status === "active"),
    [programmes],
  );

  const [name, setName] = useState("");
  const [mode, setMode] = useState<SittingMode>("training");
  const [programmeId, setProgrammeId] = useState<string>(activeProgrammes[0]?.id ?? "");
  const [cohortId, setCohortId] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        const sitting = await createSitting(orgSlug, {
          name: name.trim(),
          mode,
          programmeId,
          cohortId: cohortId || null,
          scheduledFor: scheduledFor ? new Date(scheduledFor).toISOString() : null,
        });
        onCreated(sitting.id);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [orgSlug, name, mode, programmeId, cohortId, scheduledFor, onCreated],
  );

  if (activeProgrammes.length === 0) {
    // A programme added but never activated is the usual reason, so name it.
    const drafts = programmes.filter((programme) => programme.status === "draft").map((programme) => programme.exam_name);
    return (
      <Alert tone="warning" title={drafts.length > 0 ? "Activate a programme first" : "Add a programme first"}>
        <p>
          {drafts.length > 0
            ? `${drafts.join(", ")} ${drafts.length === 1 ? "is" : "are"} still a draft. Activate it in Programmes, then come back here.`
            : `Every ${w.sitting} belongs to a programme, and that programme’s exam needs a published marking scheme. Add a programme and activate it, then come back here.`}
        </p>
        <ButtonLink href={programmesHref} themeType="b2b" variant="secondary" className="mt-2">
          Go to programmes
        </ButtonLink>
      </Alert>
    );
  }

  return (
    <Panel title="Details" className="max-w-3xl">
      <form onSubmit={submit} className="flex flex-col gap-5">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}

        <Input
          label="Name"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="March mock OSCE"
        />

        <ModeField value={mode} onChange={setMode} />

        <ProgrammeField
          value={programmeId}
          onChange={setProgrammeId}
          programmes={activeProgrammes}
        />

        {cohorts.length > 0 ? <CohortField value={cohortId} onChange={setCohortId} cohorts={cohorts} /> : null}

        <ScheduledForField value={scheduledFor} onChange={setScheduledFor} />

        <div className="flex justify-end gap-2">
          <ButtonLink href={cancelHref} themeType="b2b" variant="secondary">
            Cancel
          </ButtonLink>
          <Button themeType="b2b" variant="commit" type="submit" disabled={busy || name.trim().length === 0 || !programmeId}>
            {busy ? <Spinner label="Creating" className="text-current" /> : `Create ${w.sitting}`}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
