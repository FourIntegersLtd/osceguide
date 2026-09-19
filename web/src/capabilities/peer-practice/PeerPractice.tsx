"use client";

import { useCallback, useState } from "react";
import { HiOutlineCalendarDays, HiOutlinePlus } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CPageHeader,
  B2CSegmentedTabs,
  Button,
  ConfirmModal,
  Modal,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { listExams } from "@/capabilities/stations";
import {
  claimSlot,
  listPracticeSessions,
  listSlots,
  offerSlot,
  withdrawSlot,
  type Slot,
} from "@/capabilities/peer-practice/api";
import {
  MARKETPLACE_TABS,
  type MarketplaceTab,
} from "@/capabilities/peer-practice/marketplace/tabs";
import { MarketplaceIntroCard } from "@/capabilities/peer-practice/marketplace/MarketplaceIntroCard";
import {
  ClaimConfirmationModal,
  MarketplaceHowItWorksModal,
} from "@/capabilities/peer-practice/marketplace/modals";
import {
  OfferSlotForm,
  OFFER_SLOT_MODAL_WIDTH,
  type OfferSlotInput,
} from "@/capabilities/peer-practice/marketplace/OfferSlotForm";
import { MySlots, SlotSections } from "@/capabilities/peer-practice/marketplace/SlotSections";
import { UpcomingSessions } from "@/capabilities/peer-practice/marketplace/UpcomingSessions";
import { LivePracticeButton } from "@/capabilities/peer-practice/queue/LivePracticeButton";
import { PeerSessionScreen } from "@/capabilities/peer-practice/session/PeerSessionScreen";
import { useQueue } from "@/capabilities/peer-practice/support/useQueue";
import { longDate, meridiemTime } from "@/capabilities/peer-practice/support/time";

/**
 * Practise with another person.
 *
 * Two halves of one thing: a marketplace of arranged times, and a queue that
 * pairs you with whoever else is waiting. They were two folders and forty-one
 * files in the retiring client, connected through a context, a localStorage
 * key per exam and a polling hook each; they are one screen here because they
 * are one question — "who can I practise with?" — and the answer to it is
 * either a time or a person.
 *
 * `orgId` scopes both halves to one organisation's cohort when a surface
 * supplies it. The component itself knows only that an audience exists, which
 * is what lets an institution have this without a second implementation.
 */
export function PeerPractice({ orgId = null }: { orgId?: string | null }) {
  const [tab, setTab] = useState<MarketplaceTab>("available");
  const [reloadKey, setReloadKey] = useState(0);
  const [offering, setOffering] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [claiming, setClaiming] = useState<Slot | null>(null);
  const [claimingId, setClaimingId] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [chosenSessionId, setChosenSessionId] = useState<string | null>(null);

  // The exam is the app's, not this screen's. There used to be a dropdown
  // here over every published exam, which offered to pair somebody for an exam
  // they had never bought — and `POST /peer-practice/queue` now refuses that.
  const { code: activeExam } = useCurrentExam();
  const exams = useAsync((signal) => listExams(signal), []);
  const slots = useAsync((signal) => listSlots({ orgId }, signal), [orgId, reloadKey]);
  const mySessions = useAsync((signal) => listPracticeSessions(signal), [reloadKey]);
  const queue = useQueue(orgId);

  // Still read, but only to put a name on the exam rather than to choose one.
  const examLabel =
    (exams.data?.items ?? []).find((exam) => exam.code === activeExam)?.name ??
    (activeExam ?? "").toUpperCase();
  // The slot is offered for the exam being practised, so the form is handed
  // that one rather than the catalogue.
  const offerableExams = activeExam ? [{ code: activeExam, name: examLabel }] : [];

  // A match is the one thing that takes over the screen: both people are
  // waiting on each other, so there is nothing else worth looking at. Read
  // from the queue rather than copied into state by an effect, so the room
  // appears on the frame the match arrives on.
  const openSessionId = chosenSessionId ?? queue.matchedSessionId;

  const live = (mySessions.data?.items ?? []).find((session) => session.status !== "ended");

  const leaveSession = useCallback(() => {
    setChosenSessionId(null);
    queue.reset();
    setReloadKey((key) => key + 1);
  }, [queue]);

  const post = useCallback(
    async (input: OfferSlotInput) => {
      setPosting(true);
      setSuccess(null);
      setFailure(null);
      try {
        await offerSlot({ ...input, orgId });
        setOffering(false);
        setSuccess("Availability posted successfully!");
        setTab("myPosts");
        setReloadKey((key) => key + 1);
      } catch (cause) {
        setFailure(errorMessage(cause));
      } finally {
        setPosting(false);
      }
    },
    [orgId],
  );

  const confirmClaim = useCallback(async () => {
    const slot = claiming;
    if (!slot) return;
    setClaiming(null);
    setClaimingId(slot.id);
    setSuccess(null);
    setFailure(null);
    try {
      const session = await claimSlot(slot.id);
      setSuccess(
        `Session booked! You will practice on ${longDate(session.starts_at)} at ${meridiemTime(session.starts_at)}.`,
      );
      setTab("upcoming");
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setClaimingId(null);
      // Always refresh: the slot is gone either way, whether we took it or
      // somebody beat us to it by a fraction of a second.
      setReloadKey((key) => key + 1);
    }
  }, [claiming]);

  const confirmWithdraw = useCallback(async () => {
    const postId = withdrawing;
    setWithdrawing(null);
    if (!postId) return;
    setSuccess(null);
    setFailure(null);
    try {
      await withdrawSlot(postId);
      setSuccess("Post cancelled successfully.");
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setReloadKey((key) => key + 1);
    }
  }, [withdrawing]);

  const actions = {
    onClaim: setClaiming,
    onWithdraw: setWithdrawing,
    claimingId,
  };

  if (openSessionId) {
    return <PeerSessionScreen sessionId={openSessionId} onLeave={leaveSession} />;
  }

  return (
    <div className="w-full pb-24">
      <B2CPageHeader
        title="Practise with someone"
        subtitle="Be paired with another candidate now, or arrange a time."
        icon={HiOutlineCalendarDays}
      />

      {success && <Alert tone="success" className="mb-4">{success}</Alert>}
      {failure && <Alert tone="danger" className="mb-4">{failure}</Alert>}

      {live && (
        <Alert tone="info" className="mb-4">
          You have a practice session in progress.{" "}
          <button
            type="button"
            onClick={() => setChosenSessionId(live.id)}
            className="font-semibold underline underline-offset-2"
          >
            Rejoin it
          </button>
        </Alert>
      )}

      <div className="mb-4 flex min-w-0 flex-col gap-3 sm:mb-6 sm:flex-row sm:items-center sm:justify-between">
        <B2CSegmentedTabs items={MARKETPLACE_TABS} value={tab} onChange={setTab} aria-label="Marketplace" />

        {tab === "available" && (
          <div className="mt-2 flex w-full flex-col gap-2 sm:mt-0 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
            <LivePracticeButton queue={queue} examCode={activeExam || null} />
            <Button
              type="button"
              variant="primary"
              size="md"
              onClick={() => setOffering(true)}
              className="w-full gap-1.5 sm:w-auto"
            >
              <HiOutlinePlus className="h-3.5 w-3.5 shrink-0" />
              <span>Post Availability</span>
            </Button>
          </div>
        )}
      </div>

      <div className="mb-6 sm:mb-8">
        <MarketplaceIntroCard examLabel={examLabel} onLearnMore={() => setExplaining(true)} />
      </div>

      <div id={`tab-panel-${tab}`} role="tabpanel">
        {tab === "upcoming" ? (
          <UpcomingSessions reloadKey={reloadKey} />
        ) : (
          <AsyncBoundary state={slots} isEmpty={() => false}>
            {(page) =>
              tab === "available" ? (
                <SlotSections slots={page.items} actions={actions} />
              ) : (
                <MySlots slots={page.items} actions={actions} />
              )
            }
          </AsyncBoundary>
        )}
      </div>

      {offering && (
        <Modal
          onClose={() => setOffering(false)}
          width={OFFER_SLOT_MODAL_WIDTH}
          height="fit-content"
        >
          <OfferSlotForm
            exams={offerableExams}
            onSubmit={post}
            isLoading={posting}
            onCancel={() => setOffering(false)}
          />
        </Modal>
      )}

      <ClaimConfirmationModal
        slot={claiming}
        isClaiming={claimingId !== null}
        onConfirm={() => void confirmClaim()}
        onCancel={() => setClaiming(null)}
      />

      {explaining && <MarketplaceHowItWorksModal onClose={() => setExplaining(false)} />}

      <ConfirmModal
        isOpen={withdrawing !== null}
        onCancel={() => setWithdrawing(null)}
        onConfirm={() => void confirmWithdraw()}
        title="Cancel post?"
        message="Are you sure you want to cancel this post?"
        confirmText="Yes, cancel post"
        cancelText="Keep post"
      />
    </div>
  );
}
