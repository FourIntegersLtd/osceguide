"use client";

import { useState } from "react";
import { Alert, B2CPageHeader, Button, ButtonLink, Input, Select, cn, Panel } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMemberships } from "@/domains/assess/team/api";
import { PURPOSES, purposeCopy, type ProgrammePurpose } from "@/domains/assess/programmes/purposes";

/**
 * Start a programme by saying what it is for.
 *
 * The purpose comes first because it decides the rest: who joins, how practice
 * is marked and what people get at the end. `POST /orgs/{slug}/programmes`
 * takes an exam and nothing else, so this form has nowhere to send a purpose,
 * dates or a lead. Submitting says so and saves nothing.
 */
export function NewProgramme({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const [purpose, setPurpose] = useState<ProgrammePurpose>("placement");
  const [name, setName] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [milestoneOn, setMilestoneOn] = useState("");
  const [leadId, setLeadId] = useState("");
  const [notSaved, setNotSaved] = useState(false);

  // The lead is one of the organisation's staff, and that list is real.
  const staff = useAsync(
    (signal) => listMemberships(orgSlug, signal).then((page) => page.items),
    [orgSlug],
  );
  const copy = purposeCopy(purpose);

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        back={{ href: hrefFor("/programmes"), label: "Programmes" }}
        title="What is this programme for?"
        subtitle="Pick the purpose first. It decides who joins, how practice is marked and what people get at the end."
      />

      <form
        className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
        onSubmit={(event) => {
          event.preventDefault();
          setNotSaved(true);
        }}
      >
        <div className="flex flex-col gap-5">
          <Panel title="What is it for?">
            <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <legend className="sr-only">Purpose</legend>
              {PURPOSES.map((option) => (
                <label
                  key={option.id}
                  className={cn(
                    "flex cursor-pointer flex-col gap-1 rounded-panel border p-4",
                    option.id === purpose ? "border-accent bg-canvas" : "border-b2b-border",
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-osce-body font-semibold text-b2b-headline">{option.label}</span>
                    <input
                      type="radio"
                      name="purpose"
                      className="h-4 w-4 accent-accent"
                      checked={option.id === purpose}
                      onChange={() => setPurpose(option.id)}
                    />
                  </span>
                  <span className="text-osce-caption font-medium text-b2b-mid">{option.when}</span>
                  <span className="text-osce-meta text-b2b-headline">{option.headline}</span>
                  <span className="text-osce-meta text-b2b-mid">{option.stages.join(" → ")}</span>
                </label>
              ))}
            </fieldset>
          </Panel>

          <Panel title="Details">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Input
                label="Name"
                required
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="sm:col-span-2"
              />
              <Input
                label="Preparation starts"
                type="date"
                value={startsOn}
                onChange={(event) => setStartsOn(event.target.value)}
              />
              <Input
                label={copy.milestoneLabel}
                type="date"
                value={milestoneOn}
                onChange={(event) => setMilestoneOn(event.target.value)}
              />
              <Select
                label="Lead"
                value={leadId}
                onChange={(event) => setLeadId(event.target.value)}
                disabled={!staff.data}
                hint={staff.error ? "Could not load your staff." : undefined}
              >
                <option value="">Choose a lead</option>
                {(staff.data ?? []).map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.email ?? "No email address on file"}
                  </option>
                ))}
              </Select>
            </div>
          </Panel>

          {notSaved ? (
            <Alert tone="warning" title="Nothing was saved">
              Creating a programme with a purpose, dates and a lead needs an API route that does not exist yet.
            </Alert>
          ) : null}

          <div className="flex justify-end gap-2">
            <ButtonLink href={hrefFor("/programmes")} themeType="b2b" variant="secondary">
              Cancel
            </ButtonLink>
            <Button themeType="b2b" variant="commit" type="submit" disabled={name.trim().length === 0}>
              Create programme
            </Button>
          </div>
        </div>

        <Panel title={`${copy.label} sets up`} className="self-start">
          <dl className="flex flex-col gap-3 text-osce-meta">
            {(
              [
                ["Who joins", copy.setsUp.whoJoins],
                ["How it is marked", copy.setsUp.marking],
                ["The three stages", copy.setsUp.stages],
                ["What people get", copy.setsUp.outcome],
                ["Suggested stations", copy.setsUp.stations],
              ] as const
            ).map(([term, detail]) => (
              <div key={term}>
                <dt className="font-medium text-b2b-headline">{term}</dt>
                <dd className="text-b2b-mid">{detail}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-osce-caption text-b2b-mid">You can change any of these after you create it.</p>
        </Panel>
      </form>
    </div>
  );
}
