"use client";

import { useCallback, useState } from "react";
import { HiOutlinePlus } from "react-icons/hi2";
import Alert from "@/foundation/forms/Alert";
import {
  AsyncBoundary,
  B2CPageHeader,
  B2CSegmentedTabs,
  Button,
  ConfirmModal,
  Modal,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { failureText } from "@/capabilities/peer-practice/support/failure";
import { hasCode } from "@/foundation/platform-client";
import { useCurrentExam } from "@/foundation/session";
import {
  claimSlot,
  listMyPosts,
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
import { ListLoadError, ListLoading } from "@/capabilities/peer-practice/marketplace/listStates";
import { LivePracticeButton } from "@/capabilities/peer-practice/queue/LivePracticeButton";
import { longDate, meridiemTime } from "@/capabilities/peer-practice/support/time";

import { PeerPracticeProvider, usePeerPractice } from "./PeerPracticeProvider";

/** Every slot is thirty minutes; the retiring form never asked. */
const SLOT_MINUTES = 30;

/** A message plus a counter, so the same toast can be raised twice in a row. */
type Notice = { id: number; type: "success" | "error"; text: string };

/**
 * The marketplace: arranged times, and the button that pairs you now.
 *
 * `orgId` scopes both halves to one organisation's cohort when a surface
 * supplies it. The component itself knows only that an audience exists, which
 * is what lets an institution have this without a second implementation.
 */
export function PeerPractice({ orgId = null }: { orgId?: string | null }) {
  const shared = usePeerPractice();
  if (!shared || shared.orgId !== orgId) {
    return (
      <PeerPracticeProvider orgId={orgId}>
        <PeerPracticeContent orgId={orgId} />
      </PeerPracticeProvider>
    );
  }
  return <PeerPracticeContent orgId={orgId} />;
}

function PeerPracticeContent({ orgId }: { orgId: string | null }) {
  const shared = usePeerPractice()!;
  const [tab, setTab] = useState<MarketplaceTab>("available");
  const [reloadKey, setReloadKey] = useState(0);
  const [offering, setOffering] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [claiming, setClaiming] = useState<Slot | null>(null);
  const [claimingId, setClaimingId] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  // The exam is the app's, not this screen's: one answer, set once per account.
  const { code: activeExam } = useCurrentExam();
  const myPosts = useAsync((signal) => listMyPosts(signal), [reloadKey]);

  const say = useCallback((type: Notice["type"], text: string) => {
    setNotice((previous) => ({ id: (previous?.id ?? 0) + 1, type, text }));
  }, []);

  const reloadAll = useCallback(() => {
    setReloadKey((key) => key + 1);
    shared.refresh();
  }, [shared]);

  const post = useCallback(
    async (input: OfferSlotInput) => {
      if (!activeExam) return;
      setPosting(true);
      setNotice(null);
      try {
        await offerSlot({
          examCode: activeExam,
          startsAt: input.startsAt,
          durationMinutes: SLOT_MINUTES,
          note: input.note,
          orgId,
        });
        setOffering(false);
        say("success", "Availability posted successfully!");
        setTab("myPosts");
        reloadAll();
      } catch (cause) {
        say("error", failureText(cause, "Failed to create post. Please try again."));
      } finally {
        setPosting(false);
      }
    },
    [activeExam, orgId, reloadAll, say],
  );

  // The modal closes the moment the claim is confirmed; the card spins instead.
  const confirmClaim = useCallback(async () => {
    const slot = claiming;
    if (!slot || claimingId) return;
    setClaiming(null);
    setClaimingId(slot.id);
    setNotice(null);
    try {
      const session = await claimSlot(slot.id);
      say(
        "success",
        `Session booked! You will practice with ${session.partner_username} on ${longDate(session.starts_at)} at ${meridiemTime(session.starts_at)}.`,
      );
      setTab("upcoming");
    } catch (cause) {
      say(
        "error",
        hasCode(cause, "slot_already_claimed")
          ? "This slot has already been claimed by someone else."
          : failureText(cause, "Failed to claim slot. Please try again."),
      );
    } finally {
      setClaimingId(null);
      // The slot is gone either way, whether we took it or somebody beat us.
      reloadAll();
    }
  }, [claiming, claimingId, reloadAll, say]);

  const confirmWithdraw = useCallback(async () => {
    const postId = withdrawing;
    setWithdrawing(null);
    if (!postId) return;
    setNotice(null);
    try {
      await withdrawSlot(postId);
      say("success", "Post cancelled successfully.");
    } catch (cause) {
      say("error", failureText(cause, "Failed to cancel post. Please try again."));
    } finally {
      reloadAll();
    }
  }, [withdrawing, reloadAll, say]);

  const actions = { onClaim: setClaiming, onWithdraw: setWithdrawing, claimingId };

  return (
    <>
      <B2CPageHeader title="Marketplace" />
      <div className="w-full pb-24">
        {notice && <Alert key={notice.id} message={notice.text} type={notice.type} className="mb-4" />}

        <div className="mb-4 flex min-w-0 flex-col gap-3 sm:mb-6 sm:flex-row sm:items-center sm:justify-between md:mb-6">
          <B2CSegmentedTabs
            items={MARKETPLACE_TABS}
            value={tab}
            onChange={setTab}
            aria-label="Marketplace"
          />

          {tab === "available" && (
            <div className="mt-2 flex w-full flex-col gap-2 sm:mt-0 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
              <LivePracticeButton queue={shared.queue} examCode={activeExam || null} />
              <Button
                type="button"
                variant="primary"
                size="md"
                onClick={() => setOffering((open) => !open)}
                className="w-full gap-1.5 sm:w-auto"
              >
                <HiOutlinePlus className="h-3.5 w-3.5 shrink-0" />
                <span>Post Availability</span>
              </Button>
            </div>
          )}
        </div>

        <div className="mb-6 sm:mb-8">
          <MarketplaceIntroCard examCode={activeExam || null} onLearnMore={() => setExplaining(true)} />
        </div>

        <div id={`tab-panel-${tab}`} role="tabpanel">
          {tab === "upcoming" ? (
            <UpcomingSessions reloadKey={reloadKey} onOpenPracticeSession={shared.openSession} />
          ) : tab === "available" ? (
            <SlotSections orgId={orgId ?? null} examCode={activeExam || null} reloadKey={reloadKey} actions={actions} />
          ) : (
            <AsyncBoundary
              state={myPosts}
              isEmpty={() => false}
              loading={<ListLoading />}
              failure={(_error, retry) => (
                <ListLoadError message="Failed to load your posts. Please try again." onRetry={retry} />
              )}
            >
              {(page) => <MySlots slots={page.items} actions={actions} />}
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
              onSubmit={post}
              isLoading={posting}
              onCancel={() => setOffering(false)}
            />
          </Modal>
        )}

        <ClaimConfirmationModal
          slot={claiming}
          isClaiming={claiming !== null && claimingId === claiming.id}
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
    </>
  );
}
