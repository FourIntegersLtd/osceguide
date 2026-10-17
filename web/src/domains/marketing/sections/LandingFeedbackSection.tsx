"use client";

import {
  HiOutlineCheckCircle,
  HiOutlineExclamationCircle,
  HiOutlineLightBulb,
} from "react-icons/hi2";
import { useState } from "react";
import { Modal, ModalContent, ModalLead, cn, Spinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useToast } from "@/foundation/hooks/useToast";
import { sendSiteMessage } from "@/capabilities/help/api";
import { LandingIconBadge } from "@/domains/marketing/LandingIconBadge";
import type { LandingIconColor } from "@/domains/marketing/landingIconPalette";
import { landingSectionSurfaces } from "../landingSectionSurfaces";
import { useLandingVariant } from "../LandingVariantContext";

/*
 * "Help Us Improve" — a port of the retiring landing's two-tab feedback
 * widget ("Harsh Truth" and "Feature Wishlist"), pixel for pixel. What
 * changed is the wire: the old form posted both boxes to `/api/add_feature`;
 * `POST /site/messages` files this as `product_feedback` with the two boxes
 * composed into the body, and it accepts an anonymous sender, which is what a
 * landing page needs.
 */

type FeaturesTab = "harsh-truth" | "feature-wishlist";

const LANDING_TABS: Array<{
  id: FeaturesTab;
  label: string;
  icon: typeof HiOutlineExclamationCircle;
  color: LandingIconColor;
}> = [
  {
    id: "harsh-truth",
    label: "Harsh Truth",
    icon: HiOutlineExclamationCircle,
    color: "rose",
  },
  {
    id: "feature-wishlist",
    label: "Feature Wishlist",
    icon: HiOutlineLightBulb,
    color: "amber",
  },
];

const landingTextareaClassName =
  "font-landing-body h-40 w-full resize-none rounded-landing-card border border-landing-warm bg-landing-card px-4 py-3 text-osce-body leading-relaxed text-osce-ink-900 placeholder:text-b2c-text-muted focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent/30";

export function LandingFeedbackSection() {
  const { type: landingStyles } = useLandingVariant();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<FeaturesTab>("harsh-truth");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedback, setFeedback] = useState({
    harshTruth: "",
    featureWishlist: "",
  });

  const handleSubmit = async () => {
    if (!feedback.harshTruth.trim() && !feedback.featureWishlist.trim()) {
      return;
    }
    setIsSubmitting(true);
    try {
      // One message carrying whichever boxes were filled, labelled the way
      // the widget names them.
      const parts = [
        feedback.harshTruth.trim()
          ? `Harsh truth:\n${feedback.harshTruth.trim()}`
          : null,
        feedback.featureWishlist.trim()
          ? `Feature wishlist:\n${feedback.featureWishlist.trim()}`
          : null,
      ].filter((part): part is string => part !== null);
      await sendSiteMessage({
        kind: "product_feedback",
        body: parts.join("\n\n"),
        source: "landing/help-us-improve",
      });
      setFeedback({ harshTruth: "", featureWishlist: "" });
      setShowFeedbackModal(true);
    } catch (err) {
      toast.error(
        "We couldn't send your feedback",
        errorMessage(err) || "Please try again in a moment.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const harshTruthField = (
    <>
      <label className={`${landingStyles.itemTitle} mb-4 block text-osce-body`}>
        Tell us what you{" "}
        <span className="font-landing-heading uppercase tracking-wider text-osce-danger">
          dislike
        </span>{" "}
        about our product
        <span
          className={`${landingStyles.itemBody} mt-2 block font-normal text-osce-ink-600`}
        >
          (We promise we can take it, let&apos;s improve your experience! 💪)
        </span>
      </label>
      <textarea
        value={feedback.harshTruth}
        onChange={(e) =>
          setFeedback({ ...feedback, harshTruth: e.target.value })
        }
        className={landingTextareaClassName}
        placeholder="E.g., 'OSCE Guide is slower than a snail on a lazy day!' 😄"
      />
    </>
  );

  const featureWishlistField = (
    <>
      <label className={`${landingStyles.itemTitle} mb-4 block text-osce-body`}>
        Got a feature you wish existed?{" "}
        <span className="font-landing-heading uppercase tracking-wider text-osce-accent">
          share
        </span>{" "}
        it with us!
        <span
          className={`${landingStyles.itemBody} mt-2 block font-normal text-osce-ink-600`}
        >
          (No idea is too wild, let&apos;s make it happen!💪💪)
        </span>
      </label>
      <textarea
        value={feedback.featureWishlist}
        onChange={(e) =>
          setFeedback({ ...feedback, featureWishlist: e.target.value })
        }
        className={landingTextareaClassName}
        placeholder="E.g., 'How about an auto-pizza-ordering button when I'm hungry?'"
      />
    </>
  );

  return (
    <section
      id="feedback"
      className={`scroll-mt-20 pb-12 pt-16 sm:pt-20 ${landingSectionSurfaces.feedback}`}
    >
      <div className={landingStyles.sectionShell}>
        <div className="mb-10 text-center sm:mb-12">
          <h2 className={landingStyles.sectionTitle}>
            Help Us <span className="text-osce-accent">Improve</span>
          </h2>
          <p className={landingStyles.sectionSubtitleCentered}>
            Your feedback shapes our platform. Be honest, be bold!
          </p>
        </div>

        <div className="mx-auto max-w-4xl font-landing-body">
          <div className="mb-6 inline-flex w-full flex-wrap gap-1 rounded-[var(--landing-radius-cta,0.5rem)] border border-landing-warm bg-[color:var(--landing-card-accent,var(--b2c-surface-muted))] p-1 sm:w-auto">
            {LANDING_TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "inline-flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-[var(--landing-radius-cta,0.375rem)] px-4 py-2 font-landing-body text-osce-body font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas sm:flex-none sm:px-5",
                    isActive
                      ? "border border-landing-warm bg-landing-card text-osce-ink-900 shadow-landing-card"
                      : "border border-transparent text-b2c-text-secondary hover:text-osce-ink-900",
                  )}
                >
                  <LandingIconBadge
                    icon={Icon}
                    color={tab.color}
                    size="sm"
                    className="h-6 w-6 rounded-[7px]"
                  />
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="rounded-landing-panel border border-landing-warm bg-landing-card p-6 shadow-landing-panel sm:p-8">
            <div className={activeTab === "harsh-truth" ? "block" : "hidden"}>
              {harshTruthField}
            </div>
            <div
              className={activeTab === "feature-wishlist" ? "block" : "hidden"}
            >
              {featureWishlistField}
            </div>

            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className={cn(
                  landingStyles.ctaInk,
                  "px-8 py-3 disabled:opacity-60",
                )}
              >
                {isSubmitting ? (
                  <>
                    <Spinner size="sm" className="mr-2 text-current" label="Submitting" />
                    Submitting...
                  </>
                ) : (
                  "Submit feedback"
                )}
              </button>
            </div>
          </div>

          {showFeedbackModal && (
            <Modal
              onClose={() => setShowFeedbackModal(false)}
              width="400px"
              height="fit-content"
            >
              <ModalContent>
                <ModalLead
                  title="Thank you for your feedback"
                  description="Your insights help us improve. We will carefully review your feedback and work on making your experience even better."
                  icon={<HiOutlineCheckCircle className="h-5 w-5" />}
                  iconTone="competent"
                />
              </ModalContent>
            </Modal>
          )}
        </div>
      </div>
    </section>
  );
}
