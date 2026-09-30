"use client";

import { useState } from "react";
import {
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineClock,
  HiOutlineXMark,
} from "react-icons/hi2";
import {
  Modal,
  ModalBody,
  ModalField,
  ModalFooterActions,
  ModalHelper,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalSection,
  productTokens,
} from "@/foundation/ui";
import { updateMe } from "@/capabilities/account/api";

const { b2cSettingsFieldInput } = productTokens;

/** Whole minutes and leftover seconds of a duration, as the fields show them. */
function splitSeconds(total: number): { minutes: string; seconds: string } {
  return { minutes: String(Math.floor(total / 60)), seconds: String(total % 60) };
}

/**
 * The old "Custom timer durations" modal, field for field.
 *
 * It saves straight away rather than with the card's button, as it always did,
 * and reports through the card's own alerts. A timer left at zero is left as
 * it was, so somebody can change one without touching the other.
 */
export default function TimerSettingsModal({
  readingSeconds,
  simulationSeconds,
  needsExtraTime,
  onError,
  onSuccess,
  onClose,
}: {
  readingSeconds: number;
  simulationSeconds: number;
  needsExtraTime: boolean;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
  onClose: () => void;
}) {
  const initialReading = splitSeconds(readingSeconds);
  const initialSimulation = splitSeconds(simulationSeconds);
  const [doctorMinutes, setDoctorMinutes] = useState(initialReading.minutes);
  const [doctorSeconds, setDoctorSeconds] = useState(initialReading.seconds);
  const [simulationMinutes, setSimulationMinutes] = useState(initialSimulation.minutes);
  const [simulationSecondsField, setSimulationSecondsField] = useState(initialSimulation.seconds);
  const [isSaving, setIsSaving] = useState(false);

  const outOfRange = (value: string, max: number) =>
    value !== "" && (Number.parseInt(value, 10) < 0 || Number.parseInt(value, 10) > max);

  const handleSave = async () => {
    const doctorTotal =
      (Number.parseInt(doctorMinutes, 10) || 0) * 60 + (Number.parseInt(doctorSeconds, 10) || 0);
    const simulationTotal =
      (Number.parseInt(simulationMinutes, 10) || 0) * 60 +
      (Number.parseInt(simulationSecondsField, 10) || 0);
    if (outOfRange(doctorMinutes, 60)) {
      onError("Doctor timer minutes must be between 0 and 60");
      return;
    }
    if (outOfRange(doctorSeconds, 59)) {
      onError("Doctor timer seconds must be between 0 and 59");
      return;
    }
    if (outOfRange(simulationMinutes, 60)) {
      onError("Simulation timer minutes must be between 0 and 60");
      return;
    }
    if (outOfRange(simulationSecondsField, 59)) {
      onError("Simulation timer seconds must be between 0 and 59");
      return;
    }
    if (doctorTotal < 1 && simulationTotal < 1) {
      onError("At least one timer duration must be at least 1 second");
      return;
    }
    setIsSaving(true);
    onError("");
    try {
      await updateMe({
        needs_extra_time: needsExtraTime,
        ...(doctorTotal > 0 ? { custom_reading_seconds: doctorTotal } : {}),
        ...(simulationTotal > 0 ? { custom_simulation_seconds: simulationTotal } : {}),
      });
      onSuccess("Timer durations saved successfully!");
      onClose();
    } catch {
      onError("Failed to save timer durations. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    onError("");
    onClose();
  };

  return (
    <Modal width="min(600px, 95vw)" height="fit-content" title="Custom timer durations" onClose={handleCancel}>
      <ModalBody>
        <ModalLead
          title="Custom timer durations"
          description='Set custom timer durations for the reading and simulation phases. These durations will be used for all stations when you have "Extra Time" enabled.'
          icon={<HiOutlineClock className="h-5 w-5" />}
        />

        <ModalSection title="Reading timer (doctor information)">
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <ModalField label="Minutes" htmlFor="doctor-minutes">
                <input
                  type="number"
                  id="doctor-minutes"
                  min="0"
                  max="60"
                  value={doctorMinutes}
                  onChange={(event) => setDoctorMinutes(event.target.value)}
                  className={b2cSettingsFieldInput}
                  placeholder="0"
                />
              </ModalField>
              <ModalField label="Seconds" htmlFor="doctor-seconds">
                <input
                  type="number"
                  id="doctor-seconds"
                  min="0"
                  max="59"
                  value={doctorSeconds}
                  onChange={(event) => setDoctorSeconds(event.target.value)}
                  className={b2cSettingsFieldInput}
                  placeholder="0"
                />
              </ModalField>
            </div>
            <ModalHelper className="mt-0">
              Current: {doctorMinutes || "0"}m {doctorSeconds || "0"}s
            </ModalHelper>
          </div>
        </ModalSection>

        <ModalSection title="Simulation timer (consultation)">
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <ModalField label="Minutes" htmlFor="simulation-minutes">
                <input
                  type="number"
                  id="simulation-minutes"
                  min="0"
                  max="60"
                  value={simulationMinutes}
                  onChange={(event) => setSimulationMinutes(event.target.value)}
                  className={b2cSettingsFieldInput}
                  placeholder="0"
                />
              </ModalField>
              <ModalField label="Seconds" htmlFor="simulation-seconds">
                <input
                  type="number"
                  id="simulation-seconds"
                  min="0"
                  max="59"
                  value={simulationSecondsField}
                  onChange={(event) => setSimulationSecondsField(event.target.value)}
                  className={b2cSettingsFieldInput}
                  placeholder="0"
                />
              </ModalField>
            </div>
            <ModalHelper className="mt-0">
              Current: {simulationMinutes || "0"}m {simulationSecondsField || "0"}s
            </ModalHelper>
          </div>
        </ModalSection>

        <ModalFooterActions>
          <ModalSecondaryButton type="button" onClick={handleCancel} className="gap-2">
            <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
            Cancel
          </ModalSecondaryButton>
          <ModalPrimaryButton
            type="button"
            onClick={() => void handleSave()}
            disabled={isSaving}
            className="gap-2"
          >
            {isSaving ? (
              <>
                <HiOutlineArrowPath className="h-3.5 w-3.5 animate-spin" aria-hidden />
                Saving...
              </>
            ) : (
              <>
                <HiOutlineCheckCircle className="h-3.5 w-3.5" aria-hidden />
                Save settings
              </>
            )}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </ModalBody>
    </Modal>
  );
}
