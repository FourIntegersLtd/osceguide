"use client";

import { useState } from "react";
import {
  HiOutlineBeaker,
  HiOutlineCamera,
  HiOutlineClipboardDocumentList,
  HiOutlineDocumentText,
  HiOutlineHeart,
  HiOutlineIdentification,
  HiOutlineUser,
  HiOutlineUserCircle,
  HiOutlineUserGroup,
} from "react-icons/hi2";
import { Modal } from "@/foundation/ui";
import OrthoDoctorScreen from "./OrthoDoctorScreen";
import type { AttemptBrief } from "@/capabilities/attempt-runner/api";
import {
  DoctorInfoBulletList,
  DoctorInfoSection,
  DoctorInfoShell,
} from "@/capabilities/attempt-runner/material/DoctorInfoLayout";

/**
 * What the candidate reads before the patient is called.
 *
 * Preserve each exam's candidate layout. Ortho also selects between clinical,
 * prioritisation, communication and portfolio station formats.
 *
 * `embedded` is the consultation screen's right-hand column, where the brief
 * stays visible while the candidate talks; standalone is the reading period.
 */
export function StationBrief({
  brief,
  embedded = false,
}: {
  brief: Pick<AttemptBrief, "exam_code" | "doctor_information" | "scenario">;
  embedded?: boolean;
}) {
  const doctor = brief.doctor_information;
  const scenario = brief.scenario;

  // Ortho's stations are an interview or a trauma list rather than a
  // consultation, so the candidate's material sits flat on the document beside
  // the doctor block instead of inside it.
  if (brief.exam_code === "ortho") {
    return (
      <OrthoDoctorScreen currentStation={brief.scenario} embedded={embedded} />
    );
  }

  // PLAB and CASC brief the candidate on a role and a task; SCA hands them a
  // set of notes. Match the exam's original reading screen.
  const roleAndTask = brief.exam_code === "plab" || brief.exam_code === "casc";

  return (
    <DoctorInfoShell
      embedded={embedded}
      title={roleAndTask ? "Station information" : "Doctor information"}
    >
      {roleAndTask ? <RoleAndTaskSections brief={brief} /> : <NotesSections brief={brief} />}
      {!doctor && !scenario && (
        <p className="text-osce-body text-b2c-text-muted">
          There is no written brief for this station.
        </p>
      )}
    </DoctorInfoShell>
  );
}

/** PLAB and CASC: who you are, what you know, what you are asked to do. */
function RoleAndTaskSections({ brief }: { brief: Pick<AttemptBrief, "exam_code" | "doctor_information" | "scenario"> }) {
  const doctor = brief.doctor_information;
  if (brief.exam_code === "casc") {
    return <DoctorInfoSection title="Your Role" icon={HiOutlineUserCircle} iconTone="primary">
      <p>{doctor?.doctor_task}</p>
    </DoctorInfoSection>;
  }
  return (
    <>
      {(doctor?.doctor_identity || doctor?.doctor_task) && (
        <DoctorInfoSection title="Your Role" icon={HiOutlineUserCircle} iconTone="primary">
          <p>{doctor.doctor_identity || doctor.doctor_task}</p>
        </DoctorInfoSection>
      )}
      {doctor?.patient_information?.length ? (
        <DoctorInfoSection title="Patient Information" icon={HiOutlineUser} iconTone="emerald">
          <DoctorInfoBulletList items={doctor.patient_information} />
        </DoctorInfoSection>
      ) : null}
      {doctor?.task_instructions && (
        <DoctorInfoSection
          title="Your Task"
          icon={HiOutlineClipboardDocumentList}
          iconTone="amber"
        >
          <p>{doctor.task_instructions}</p>
        </DoctorInfoSection>
      )}
    </>
  );
}

/** SCA: the notes in front of a GP, in the order the old screen drew them. */
function NotesSections({ brief }: { brief: Pick<AttemptBrief, "exam_code" | "doctor_information" | "scenario"> }) {
  const doctor = brief.doctor_information;
  if (!doctor) return null;

  return (
    <>
      <Photos urls={doctor.photos ?? []} />

      {doctor.patient_biodata && (
        <DoctorInfoSection title="Patient Biodata" icon={HiOutlineIdentification} iconTone="primary">
          <p>{doctor.patient_biodata}</p>
        </DoctorInfoSection>
      )}
      {doctor.recent_notes?.length ? (
        <DoctorInfoSection title="Recent Notes" icon={HiOutlineDocumentText} iconTone="sky">
          <DoctorInfoBulletList items={doctor.recent_notes} />
        </DoctorInfoSection>
      ) : null}
      {doctor.current_medications?.length ? (
        <DoctorInfoSection title="Current Medications" icon={HiOutlineBeaker} iconTone="emerald">
          <DoctorInfoBulletList items={doctor.current_medications} />
        </DoctorInfoSection>
      ) : null}
      {doctor.past_medical_history?.length ? (
        <DoctorInfoSection title="Past Medical History" icon={HiOutlineHeart} iconTone="rose">
          <DoctorInfoBulletList items={doctor.past_medical_history} />
        </DoctorInfoSection>
      ) : null}
      {doctor.social_history?.length ? (
        <DoctorInfoSection title="Social History" icon={HiOutlineUserGroup} iconTone="amber">
          <DoctorInfoBulletList items={doctor.social_history} />
        </DoctorInfoSection>
      ) : null}
      {doctor.recent_investigations?.length ? (
        <DoctorInfoSection title="Recent Investigations" icon={HiOutlineBeaker} iconTone="sky">
          <DoctorInfoBulletList items={doctor.recent_investigations} />
        </DoctorInfoSection>
      ) : null}
    </>
  );
}

/**
 * Images, click to enlarge.
 *
 * A plain `<img>` rather than `next/image`: these are absolute URLs on hosts
 * this app does not configure, and an unconfigured host is a runtime error
 * rather than a slow image.
 */
function Photos({
  urls,
  title = "Photos",
  icon = HiOutlineCamera,
}: {
  urls: string[];
  title?: string;
  icon?: typeof HiOutlineCamera;
}) {
  const [enlarged, setEnlarged] = useState<string | null>(null);
  if (urls.length === 0) return null;

  return (
    <>
      <DoctorInfoSection title={title} icon={icon} iconTone="sky">
        <div className="mb-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {urls.map((url, index) => (
            <button
              key={url}
              type="button"
              className="group relative text-left"
              onClick={() => setEnlarged(url)}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={url}
                alt={`Medical image ${index + 1}`}
                className="h-40 w-full rounded-md object-cover transition-transform duration-300 group-hover:scale-[1.01]"
              />
            </button>
          ))}
        </div>
        <p className="text-center text-osce-body text-b2c-text-muted">Click to enlarge</p>
      </DoctorInfoSection>

      {enlarged && (
        <Modal onClose={() => setEnlarged(null)} width="min(95vw, 56rem)" height="fit-content">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={enlarged} alt="Enlarged" className="h-auto w-full rounded-md" />
        </Modal>
      )}
    </>
  );
}
