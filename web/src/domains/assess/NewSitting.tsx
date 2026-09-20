"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Button, Card, Input, PageHeader, Spinner, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createSitting, listProgrammes } from "@/domains/assess/api";

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
  programmes: { id: string; exam_name: string; exam_code: string; status: string }[];
  onCreated: (sittingId: string) => void;
}) {
  const activeProgrammes = useMemo(
    () => programmes.filter((programme) => programme.status === "active"),
    [programmes],
  );

  const [name, setName] = useState("");
  const [mode, setMode] = useState<"training" | "exam">("training");
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
        A sitting is bound to a programme whose exam has a published rubric. Add an active programme
        under Authoring and come back.
      </Alert>
    );
  }

  const selected = activeProgrammes.find((p) => p.id === programmeId) ?? activeProgrammes[0];

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

        <fieldset className="flex flex-col gap-1.5">
          <legend className="text-sm font-medium text-ink">Mode</legend>
          <div className="flex gap-2">
            {(["training", "exam"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setMode(option)}
                aria-pressed={mode === option}
                className={cn(
                  "rounded-control border px-3 py-1.5 text-sm capitalize",
                  mode === option
                    ? "border-accent bg-accent text-ink-inverse"
                    : "border-border-strong bg-surface text-ink-muted hover:text-ink",
                )}
              >
                {option}
              </button>
            ))}
          </div>
          <p className="text-sm text-ink-muted">
            {mode === "exam"
              ? "One candidate through every station, at most twelve. Trainees cannot be appended once it runs."
              : "Each trainee is paired with one station, and they rotate."}
          </p>
        </fieldset>

        <Select
          label="Programme"
          value={programmeId}
          onChange={setProgrammeId}
          options={activeProgrammes.map((programme) => ({
            value: programme.id,
            label: `${programme.exam_name} (${programme.exam_code})`,
          }))}
        />

        {selected ? (
          <p className="text-sm text-ink-muted">
            Marking uses the published rubric bound to {selected.exam_name}. You do not pick a
            separate feedback template.
          </p>
        ) : null}

        <Input
          label="Scheduled for"
          type="datetime-local"
          value={scheduledFor}
          onChange={(event) => setScheduledFor(event.target.value)}
          hint="Leave empty to schedule it later."
        />

        <div className="flex justify-end">
          <Button type="submit" disabled={busy || name.trim().length === 0 || !programmeId}>
            {busy ? <Spinner label="Creating" /> : "Create sitting"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-ink">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
