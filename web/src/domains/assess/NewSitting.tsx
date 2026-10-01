"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Button, Card, Input, PageHeader, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createSitting, listProgrammes, type Programme, type SittingMode } from "@/domains/assess/api";
import { ModeField, ProgrammeField, ScheduledForField } from "@/domains/assess/SittingFields";

/** Schedule a sitting against a programme (exam + published rubric). */
export function NewSitting({ orgSlug }: { orgSlug: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const programmes = useAsync(
    (signal) => listProgrammes(orgSlug, signal).then((page) => page.items),
    [orgSlug],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Schedule a sitting" description="An examination or a training session." />
      <AsyncBoundary state={programmes}>
        {(items) => (
          <Form
            orgSlug={orgSlug}
            programmes={items}
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
  onCreated,
}: {
  orgSlug: string;
  programmes: Programme[];
  onCreated: (sittingId: string) => void;
}) {
  const activeProgrammes = useMemo(
    () => programmes.filter((programme) => programme.status === "active"),
    [programmes],
  );

  const [name, setName] = useState("");
  const [mode, setMode] = useState<SittingMode>("training");
  const [programmeId, setProgrammeId] = useState<string>(activeProgrammes[0]?.id ?? "");
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
          scheduledFor: scheduledFor ? new Date(scheduledFor).toISOString() : null,
        });
        onCreated(sitting.id);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [orgSlug, name, mode, programmeId, scheduledFor, onCreated],
  );

  if (activeProgrammes.length === 0) {
    return (
      <Alert tone="warning" title="Add a programme first">
        Every sitting belongs to a programme, and that programme’s exam needs a published marking scheme. Set up a programme under Authoring, then come back here.
      </Alert>
    );
  }

  return (
    <Card>
      <form onSubmit={submit} className="flex max-w-xl flex-col gap-4">
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

        <ScheduledForField value={scheduledFor} onChange={setScheduledFor} />

        <div className="flex justify-end">
          <Button type="submit" disabled={busy || name.trim().length === 0 || !programmeId}>
            {busy ? <Spinner label="Creating" /> : "Create sitting"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
