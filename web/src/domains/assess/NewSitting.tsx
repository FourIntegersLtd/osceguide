"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AsyncBoundary, Button, Card, Input, PageHeader, Spinner, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { createSitting, listFeedbackTemplates, listProgrammes } from "@/domains/assess/api";

/**
 * Schedule a sitting.
 *
 * The only genuinely required choice is the feedback template version: the
 * backend binds it with a NOT NULL foreign key, so a sitting cannot exist
 * without one and marking can never be undefined after the fact. Only
 * published versions are offered, because only those can be bound.
 */
export function NewSitting({ orgSlug }: { orgSlug: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const options = useAsync(
    async (signal) => {
      const [programmes, templates] = await Promise.all([
        listProgrammes(orgSlug, signal),
        listFeedbackTemplates(orgSlug, signal),
      ]);
      // Templates carry their versions inline. Only published ones can be
      // bound, so an org with templates but nothing published must be told
      // that rather than shown an empty select.
      return {
        programmes: programmes.items,
        templates: templates.items.map((template) => ({
          template,
          versions: (template.versions ?? []).filter((version) => version.status === "published"),
        })),
      };
    },
    [orgSlug],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Schedule a sitting" description="An examination or a training session." />
      <AsyncBoundary state={options}>
        {(data) => (
          <Form
            orgSlug={orgSlug}
            programmes={data.programmes}
            templates={data.templates}
            onCreated={(id) => router.push(hrefFor(`/sittings/${id}`))}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

type TemplateOption = {
  template: { id: string; title: string };
  versions: { id: string; version: number }[];
};

function Form({
  orgSlug,
  programmes,
  templates,
  onCreated,
}: {
  orgSlug: string;
  programmes: { id: string; exam_name: string; status: string }[];
  templates: TemplateOption[];
  onCreated: (sittingId: string) => void;
}) {
  const bindable = useMemo(
    () =>
      templates.flatMap(({ template, versions }) =>
        versions.map((version) => ({
          id: version.id,
          label: `${template.title} · v${version.version}`,
        })),
      ),
    [templates],
  );

  const [name, setName] = useState("");
  const [mode, setMode] = useState<"training" | "exam">("training");
  const [programmeId, setProgrammeId] = useState<string>(programmes[0]?.id ?? "");
  const [versionId, setVersionId] = useState<string>(bindable[0]?.id ?? "");
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
          programmeId: programmeId || null,
          feedbackTemplateVersionId: versionId,
          scheduledFor: scheduledFor ? new Date(scheduledFor).toISOString() : null,
        });
        onCreated(sitting.id);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [orgSlug, name, mode, programmeId, versionId, scheduledFor, onCreated],
  );

  if (bindable.length === 0) {
    return (
      <Alert tone="warning" title="Publish a feedback template first">
        A sitting is bound to a published feedback template version, so marking can never be
        undefined afterwards. Publish one and come back.
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
          options={[
            { value: "", label: "No programme" },
            ...programmes.map((programme) => ({
              value: programme.id,
              label: `${programme.exam_name}${programme.status === "active" ? "" : ` (${programme.status})`}`,
            })),
          ]}
        />

        <Select
          label="Feedback template"
          value={versionId}
          onChange={setVersionId}
          options={bindable.map((option) => ({ value: option.id, label: option.label }))}
        />

        <Input
          label="Scheduled for"
          type="datetime-local"
          value={scheduledFor}
          onChange={(event) => setScheduledFor(event.target.value)}
          hint="Leave empty to schedule it later."
        />

        <div className="flex justify-end">
          <Button type="submit" disabled={busy || name.trim().length === 0}>
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
