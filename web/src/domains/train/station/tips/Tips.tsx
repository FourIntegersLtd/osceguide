import React from "react";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { motion } from "framer-motion";
import TipContent from "./TipContent";
import {
  ModalContent,
  ModalHelper,
  ModalTitle,
} from "@/foundation/ui";
import {
  B2CPanelCard,
  B2CPanelCardHeader,
  B2CPanelCardBody,
} from "@/foundation/ui";

interface TipsProps {
  duration?: number;
}

const Tips: React.FC<TipsProps> = ({ duration = 120 }) => {
  const spinTransition = { duration: 1, repeat: Infinity, ease: "linear" as const };

  return (
    <ModalContent className="space-y-3">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-3"
      >
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Generating your feedback</B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-3">
            <div className="flex items-start gap-3">
              <motion.div
                animate={{ rotate: 360 }}
                transition={spinTransition}
                className="mt-0.5 shrink-0"
              >
                <AiOutlineLoading3Quarters className="h-4 w-4 text-osce-accent" />
              </motion.div>
              <div className="min-w-0">
                <ModalTitle>Hang tight</ModalTitle>
                <ModalHelper>
                  This usually takes one to three minutes. Let&apos;s use the
                  time to learn something new; you&apos;ll be taken through the
                  moment your feedback is ready.
                </ModalHelper>
              </div>
            </div>

            <div>
              <div
                className="h-1.5 w-full overflow-hidden rounded-md bg-b2c-surface-muted"
                role="progressbar"
                aria-label="Marking in progress"
              >
                <motion.div
                  className="h-full w-1/3 rounded-md bg-osce-accent"
                  animate={{ x: ["-100%", "300%"] }}
                  transition={{ duration: Math.max(2, duration / 60), repeat: Infinity, ease: "easeInOut" }}
                />
              </div>
              <p className="mt-1.5 text-osce-meta text-b2c-text-muted">
                Reviewing your consultation and writing feedback
              </p>
            </div>
          </B2CPanelCardBody>
        </B2CPanelCard>

        <TipContent />
      </motion.div>
    </ModalContent>
  );
};

export default Tips;
