"use client";

import { B2CPageHeader, Badge, Button, EmptyState, Panel } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import {
  Columns,
  Completion,
  Person,
  PreviewNotice,
  SimpleTable,
  StageStrip,
  StationList,
} from "@/domains/assess/programmes/parts";
import {
  PREVIEW_PROGRAMME_DETAILS,
  type CpdProgramme,
  type OnboardingProgramme,
  type PlacementProgramme,
  type ProgrammeDetailData,
  type RecruitmentCandidate,
  type RecruitmentProgramme,
} from "@/domains/assess/programmes/preview";
import { purposeCopy } from "@/domains/assess/programmes/purposes";

/**
 * One programme, laid out for what it is for.
 *
 * The four purposes share a header and a three-stage strip and differ below
 * it: a placement shows readiness, recruitment shows findings without a score,
 * onboarding shows sign-offs and CPD shows guidance updates and logged hours.
 * No route returns any of it yet, so the page reads the sample in `preview.ts`.
 */
export function ProgrammeDetail({ programmeId }: { programmeId: string }) {
  const { hrefFor } = useSurface();
  const back = { href: hrefFor("/programmes"), label: "Programmes" };
  const programme = PREVIEW_PROGRAMME_DETAILS.find((entry) => entry.id === programmeId);

  if (!programme) {
    return (
      <div className="flex flex-col gap-6">
        <B2CPageHeader back={back} title="Programme" />
        <EmptyState
          title="No such programme"
          description="Programme pages show sample data until the API can return one."
        />
      </div>
    );
  }

  const copy = purposeCopy(programme.purpose);
  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        back={back}
        eyebrow={`${copy.label} · ${copy.when}`}
        title={programme.name}
        subtitle={programme.summary}
        action={
          <Button themeType="b2b" variant="commit" disabled title="Not connected yet">
            {copy.addLabel}
          </Button>
        }
      />
      <PreviewNotice needs="A programme has no purpose, people or progress on the API." />
      <StageStrip titles={copy.stages} stages={programme.stages} />
      <Body programme={programme} />
    </div>
  );
}

function Body({ programme }: { programme: ProgrammeDetailData }) {
  switch (programme.purpose) {
    case "placement":
      return <Placement programme={programme} />;
    case "recruitment":
      return <Recruitment programme={programme} />;
    case "onboarding":
      return <Onboarding programme={programme} />;
    case "cpd":
      return <Cpd programme={programme} />;
  }
}

function Placement({ programme }: { programme: PlacementProgramme }) {
  return (
    <Columns
      main={
        <Panel title="Students">
          <SimpleTable
            rows={programme.students}
            rowKey={(student) => student.email}
            columns={[
              { header: "Student", cell: (student) => <Person name={student.name} detail={student.email} /> },
              { header: "Stage", cell: (student) => student.stage },
              { header: "Stations", cell: (student) => <span className="tabular-nums">{student.stations}</span> },
              {
                header: "Readiness",
                cell: (student) => (
                  <Badge
                    variant={
                      student.readiness === "Ready"
                        ? "success"
                        : student.readiness === "Needs support"
                          ? "warning"
                          : "neutral"
                    }
                    dot
                  >
                    {student.readiness}
                  </Badge>
                ),
              },
            ]}
          />
          <p className="mt-3 text-osce-caption text-b2b-mid">
            Showing {programme.students.length} of {programme.total} students
          </p>
        </Panel>
      }
      side={
        <>
          <Panel title="First patient contact">
            <p className="text-osce-title font-semibold text-b2b-headline">{programme.firstContact.date}</p>
            <p className="mt-1 text-osce-meta text-b2b-mid">{programme.firstContact.note}</p>
          </Panel>
          <Panel title="Tutor sessions">
            <ul className="flex flex-col divide-y divide-b2b-border">
              {programme.sessions.map((session) => (
                <li key={session.name} className="flex items-start justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                  <Person name={session.name} detail={session.when} />
                  <Badge variant="neutral">{session.booked ? "Booked" : "Open"}</Badge>
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="Stations">
            <StationList stations={programme.stations} />
          </Panel>
        </>
      }
    />
  );
}

/** Three counts, never a total: recruitment findings are deliberately not a score. */
function Findings({ findings }: { findings: RecruitmentCandidate["findings"] }) {
  if (!findings) return <span className="text-b2b-mid">Not ready</span>;
  return (
    <span className="flex flex-wrap gap-1.5">
      <Badge variant="success">{findings.green} did well</Badge>
      <Badge variant="warning">{findings.amber} to improve</Badge>
      <Badge variant="danger">{findings.red} not done</Badge>
    </span>
  );
}

function FindingList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-osce-meta font-medium text-b2b-headline">{title}</h3>
      <ul className="mt-1.5 flex list-disc flex-col gap-1 pl-5 text-osce-meta text-b2b-mid">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function Recruitment({ programme }: { programme: RecruitmentProgramme }) {
  const { spotlight } = programme;
  return (
    <Columns
      main={
        <>
          <Panel title="Candidates">
            <SimpleTable
              rows={programme.candidates}
              rowKey={(candidate) => candidate.name}
              columns={[
                { header: "Candidate", cell: (candidate) => <Person name={candidate.name} detail={candidate.status} /> },
                { header: "Findings", cell: (candidate) => <Findings findings={candidate.findings} /> },
                { header: "Review", cell: (candidate) => candidate.review },
                { header: "Interview pack", cell: (candidate) => (candidate.packReady ? "Ready" : "Not yet") },
              ]}
            />
            <p className="mt-3 text-osce-caption text-b2b-mid">
              No score and no recommendation. The decision stays with your panel.
            </p>
          </Panel>
          <Panel title={`Findings for ${spotlight.name}`}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <FindingList title="Did well" items={spotlight.didWell} />
              <FindingList title="Needs improving" items={spotlight.toImprove} />
              <FindingList title="Not done" items={spotlight.notDone} />
            </div>
          </Panel>
        </>
      }
      side={
        <>
          <Panel title="How candidates join">
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-osce-meta text-b2b-mid">
              {programme.howCandidatesJoin.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Panel>
          <Panel title="Stations">
            <StationList stations={programme.stations} />
          </Panel>
        </>
      }
    />
  );
}

function Onboarding({ programme }: { programme: OnboardingProgramme }) {
  return (
    <Columns
      main={
        <>
          <Panel title="Modules">
            <ul className="flex flex-col divide-y divide-b2b-border">
              {programme.modules.map((module) => (
                <li key={module.title} className="flex items-center justify-between gap-4 py-2.5 first:pt-0 last:pb-0">
                  <Person name={module.title} detail={module.stage} />
                  <Completion value={module.completion} />
                </li>
              ))}
            </ul>
          </Panel>
          <Panel title="New starters">
            <SimpleTable
              rows={programme.starters}
              rowKey={(starter) => starter.name}
              columns={[
                { header: "New starter", cell: (starter) => <Person name={starter.name} detail={starter.started} /> },
                { header: "Stage", cell: (starter) => starter.stage },
                { header: "Supervisor", cell: (starter) => starter.supervisor },
                {
                  header: "Sign-off",
                  cell: (starter) => (
                    <Badge variant={starter.signOff === "Signed off" ? "success" : "neutral"} dot>
                      {starter.signOff}
                    </Badge>
                  ),
                },
              ]}
            />
          </Panel>
        </>
      }
      side={
        <>
          <Panel title="Signed off for independent clinics">
            <p className="text-osce-title font-semibold tabular-nums text-b2b-headline">
              {programme.signedOff.ready} of {programme.signedOff.total}
            </p>
          </Panel>
          <Panel title="Waiting for your sign-off">
            <ul className="flex flex-col divide-y divide-b2b-border">
              {programme.waiting.map((entry) => (
                <li key={entry.name} className="py-2.5 first:pt-0 last:pb-0">
                  <Person name={entry.name} detail={entry.detail} />
                </li>
              ))}
            </ul>
          </Panel>
        </>
      }
    />
  );
}

function Cpd({ programme }: { programme: CpdProgramme }) {
  return (
    <div className="flex flex-col gap-5">
      <Panel title="Guidance updates">
        <ul className="flex flex-col divide-y divide-b2b-border">
          {programme.updates.map((update) => (
            <li key={update.title} className="flex items-center justify-between gap-4 py-2.5 first:pt-0 last:pb-0">
              <Person name={update.title} detail={update.meta} />
              <Completion value={update.completion} />
            </li>
          ))}
        </ul>
      </Panel>
      <Panel title="Staff">
        <SimpleTable
          rows={programme.staff}
          rowKey={(member) => member.name}
          columns={[
            { header: "Name", cell: (member) => <Person name={member.name} detail={member.role} /> },
            { header: "CPD logged", cell: (member) => <span className="tabular-nums">{member.hours}</span> },
            { header: "Last practice", cell: (member) => member.lastPractice },
            { header: "Certificate", cell: (member) => (member.certificate ? "Available" : "Not yet") },
          ]}
        />
        <p className="mt-3 text-osce-caption text-b2b-mid">
          Showing {programme.staff.length} of {programme.total} staff
        </p>
      </Panel>
    </div>
  );
}
