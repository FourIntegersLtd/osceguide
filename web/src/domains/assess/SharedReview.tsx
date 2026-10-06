"use client";

import { useState } from "react";
import { Alert, B2CPageHeader, B2CSegmentedTabs, BandPill, Button, ButtonLink, EmptyState, Textarea, type BandVariant, Panel } from "@/foundation/ui";
import { useSurface } from "@/capabilities";

type Agreement = "agree" | "partly" | "disagree";

/**
 * Shown because this screen has no API behind it yet.
 *
 * `needs` names the missing route in plain words, so the notice doubles as the
 * to-do a reviewer reads off the screen.
 */
function PreviewNotice({ needs }: { needs: string }) {
  return (
    <Alert tone="warning" title="Sample data">
      This screen is not connected yet, so the people and numbers on it are examples. {needs}
    </Alert>
  );
}

/** What the screen needs from a shared-review route, which does not exist. */
interface SharedReviewRequest {
  id: string;
  trainee: string;
  firstName: string;
  station: string;
  context: string;
  requested: string;
  marking: { domain: string; band: BandVariant; score: string }[];
  overall: { band: BandVariant; score: string };
  excerpt: { at: string; speaker: "Doctor" | "Patient"; text: string }[];
  question: string;
  shared: string;
}

const PREVIEW_REQUEST: SharedReviewRequest = {
  id: "sample",
  trainee: "Dr Tom Reid",
  firstName: "Tom",
  station: "Painless jaundice",
  context:
    "Tom sat this station on his own on 28 September and asked you to look at it. It is not part of a sitting.",
  requested: "Requested yesterday",
  overall: { band: "competent", score: "20/27" },
  marking: [
    { domain: "Data gathering and diagnosis", band: "competent", score: "7/9" },
    { domain: "Clinical management", band: "developing", score: "5/9" },
    { domain: "Relating to others", band: "competent", score: "8/9" },
  ],
  excerpt: [
    { at: "02:14", speaker: "Doctor", text: "What has been worrying you most about this?" },
    { at: "02:20", speaker: "Patient", text: "Honestly, my dad had something with his pancreas." },
    {
      at: "07:40",
      speaker: "Doctor",
      text: "I'd like to refer you urgently, within two weeks, to get a scan. What do you think of that?",
    },
    { at: "07:52", speaker: "Patient", text: "Right. Okay, if that is what is needed." },
    { at: "10:55", speaker: "Doctor", text: "If anything changes, give us a call." },
  ],
  question: "I keep losing marks on the plan. Did I agree it with him this time?",
  shared: "Shared 28 Sep · transcript and Athena's marks",
};

const AGREEMENT: { id: Agreement; label: string }[] = [
  { id: "agree", label: "Agree" },
  { id: "partly", label: "Partly" },
  { id: "disagree", label: "Disagree" },
];

/**
 * A trainee's own practice, sent to a supervisor for a second opinion.
 *
 * Not a sitting and not a mark: the reply goes to the trainee only. The API
 * has reviews for exam slots and nothing for shared practice, so the request
 * is a sample, nothing links here yet and sending says it saved nothing.
 */
export function SharedReview({ reviewId }: { reviewId: string }) {
  const { hrefFor } = useSurface();
  const [agreement, setAgreement] = useState<Agreement>("partly");
  const [feedback, setFeedback] = useState("");
  const [notSent, setNotSent] = useState(false);
  const back = { href: hrefFor("/dashboard"), label: "Overview" };
  const request = PREVIEW_REQUEST.id === reviewId ? PREVIEW_REQUEST : null;

  if (!request) {
    return (
      <div className="flex flex-col gap-6">
        <B2CPageHeader back={back} title="Review request" />
        <EmptyState
          title="No such review request"
          description="Shared reviews show sample data until the API can return one."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        back={back}
        eyebrow="Review request · personal practice"
        title={`${request.trainee} · ${request.station}`}
        subtitle={`${request.context} ${request.requested}.`}
      />
      <PreviewNotice needs="There is no shared-review route to read a request from or send feedback to." />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-5">
          <Panel
            title="Athena's marking"
            actions={
              <span className="flex items-center gap-2 text-osce-meta tabular-nums text-b2b-mid">
                <BandPill variant={request.overall.band} />
                {request.overall.score}
              </span>
            }
          >
            <ul className="flex flex-col divide-y divide-b2b-border">
              {request.marking.map((row) => (
                <li key={row.domain} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                  <span className="text-osce-body text-b2b-headline">{row.domain}</span>
                  <span className="flex items-center gap-2 text-osce-meta tabular-nums text-b2b-mid">
                    <BandPill variant={row.band} compact />
                    {row.score}
                  </span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Transcript">
            <ol className="flex flex-col gap-3">
              {request.excerpt.map((turn) => (
                <li key={turn.at} className="grid grid-cols-[3.5rem_minmax(0,1fr)] gap-3 text-osce-body">
                  <span className="text-osce-meta tabular-nums text-b2b-mid">{turn.at}</span>
                  <span>
                    <span className="block text-osce-caption font-medium text-b2b-mid">{turn.speaker}</span>
                    <span className="text-b2b-headline">{turn.text}</span>
                  </span>
                </li>
              ))}
            </ol>
          </Panel>
        </div>

        <div className="flex min-w-0 flex-col gap-5">
          <Panel title={`${request.firstName}'s question`}>
            <blockquote className="text-osce-body text-b2b-headline">&ldquo;{request.question}&rdquo;</blockquote>
            <p className="mt-2 text-osce-caption text-b2b-mid">{request.shared}</p>
          </Panel>

          <Panel title="Your feedback">
            <form
              className="flex flex-col gap-4"
              onSubmit={(event) => {
                event.preventDefault();
                setNotSent(true);
              }}
            >
              <div className="flex flex-col gap-2">
                <p className="text-osce-meta font-medium text-b2b-headline">Do you agree with Athena&apos;s marking?</p>
                <B2CSegmentedTabs
                  compact
                  items={AGREEMENT}
                  value={agreement}
                  onChange={setAgreement}
                  aria-label="Do you agree with Athena's marking?"
                />
              </div>
              <Textarea
                label={`Feedback for ${request.firstName}`}
                rows={6}
                value={feedback}
                onChange={(event) => setFeedback(event.target.value)}
                hint={`Goes to ${request.firstName} only. It is not a mark and does not appear in sitting results.`}
              />
              {notSent ? (
                <Alert tone="warning" title="Nothing was sent">
                  Sending feedback on shared practice needs an API route that does not exist yet.
                </Alert>
              ) : null}
              <div className="flex justify-end gap-2">
                <ButtonLink href={back.href} themeType="b2b" variant="secondary">
                  Later
                </ButtonLink>
                <Button themeType="b2b" variant="commit" type="submit" disabled={feedback.trim().length === 0}>
                  Send to {request.firstName}
                </Button>
              </div>
            </form>
          </Panel>
        </div>
      </div>
    </div>
  );
}
