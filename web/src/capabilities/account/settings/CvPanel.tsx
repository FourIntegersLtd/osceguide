"use client";

import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  HiOutlineAcademicCap,
  HiOutlineBeaker,
  HiOutlineDocument,
  HiOutlineBriefcase,
  HiOutlineClipboardDocumentCheck,
  HiOutlineCloudArrowUp,
  HiOutlineCog8Tooth,
  HiOutlineCurrencyPound,
  HiOutlineNewspaper,
  HiOutlineUser,
  HiOutlineXMark,
} from "react-icons/hi2";
import { LuAward, LuCrown, LuPresentation, LuTrophy } from "react-icons/lu";
import type { ComponentType } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Button,
  ModalHelper,
  Spinner,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { listCvs, uploadCv, type CvRead, type StructuredCv } from "@/capabilities/account/api";

/**
 * The CV an orthopaedic applicant uploads, and the sections it is read into.
 *
 * The Ortho interview is scored off a portfolio rather than a consultation, so
 * the CV is not a nice-to-have on that arm — it is the material the practice
 * questions are generated from. The retiring client had it inside the profile;
 * this port had neither the screen nor a caller for `POST /cv`, which had been
 * served for weeks, so an applicant had no way to give us the one document the
 * interview is built on.
 *
 * Uploading answers a row and a status, not a parsed CV: the PDF is read by a
 * background job. So the panel polls while a row is `processing` rather than
 * pretending the sections are instant — the old copy told people "about 60
 * seconds", and a screen that goes quiet for a minute reads as a failed upload.
 */

const SECTIONS: { key: keyof StructuredCv; title: string; icon: ComponentType<{ className?: string }> }[] = [
  { key: "summary", title: "Professional Summary", icon: HiOutlineUser },
  { key: "experience", title: "Clinical Experience", icon: HiOutlineBriefcase },
  { key: "education", title: "Education & Training", icon: HiOutlineAcademicCap },
  { key: "research", title: "Research", icon: HiOutlineBeaker },
  { key: "publications", title: "Publications", icon: HiOutlineNewspaper },
  { key: "audits", title: "Audits & QIP", icon: HiOutlineClipboardDocumentCheck },
  { key: "teaching", title: "Teaching & Supervision", icon: LuPresentation },
  { key: "leadership", title: "Leadership & Management", icon: LuCrown },
  { key: "achievements", title: "Awards & Recognition", icon: LuTrophy },
  { key: "skills", title: "Skills & Competencies", icon: HiOutlineCog8Tooth },
  { key: "grants", title: "Grants & Funding", icon: HiOutlineCurrencyPound },
  { key: "courses", title: "Professional Development", icon: LuAward },
];

const MAX_BYTES = 10 * 1024 * 1024;

export function CvPanel() {
  const state = useAsync((signal) => listCvs(signal), []);
  const [pending, setPending] = useState(false);
  const reload = state.reload;

  /*
   * Poll while the newest upload is still being read. The interval lives here
   * rather than in `useAsync` because "is it done yet" is a property of the
   * data, and the data is the thing the hook just returned.
   */
  const processing = state.data?.cvs?.some((cv) => cv.status === "processing") ?? false;
  useEffect(() => {
    if (!processing && !pending) return;
    const timer = window.setInterval(() => reload(), 5000);
    return () => window.clearInterval(timer);
  }, [processing, pending, reload]);

  return (
    <AsyncBoundary state={state}>
      {(list) => {
        const latest: CvRead | undefined = list.cvs?.[0];
        return (
          <B2CPanelCard className="mt-0">
            <B2CPanelCardHeader>
              <HiOutlineDocument className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden />
              Your CV
            </B2CPanelCardHeader>
            <B2CPanelCardBody className="space-y-4">
              <ModalHelper className="mt-0">
                Upload the CV you will bring to the interview. We read it into
                sections and base your practice questions on what is in it.
              </ModalHelper>
              <Upload
                onUploaded={() => {
                  setPending(true);
                  reload();
                }}
                onSettled={() => setPending(false)}
              />
              {latest?.status === "processing" ? (
                <p className="flex items-center gap-2 text-osce-meta text-b2c-text-muted">
                  <Spinner label="Reading" /> Reading {latest.original_filename} — this takes about
                  a minute.
                </p>
              ) : null}
              {latest?.status === "failed" ? (
                <Alert tone="danger">
                  {latest.error ?? "We could not read that CV. Please try another file."}
                </Alert>
              ) : null}
              {latest?.structured ? <Sections structured={latest.structured} /> : null}
            </B2CPanelCardBody>
            {latest && latest.status === "completed" ? (
              <B2CPanelCardFooter>
                <p className="text-osce-meta text-b2c-text-muted">
                  {latest.original_filename} · uploaded{" "}
                  {new Date(latest.uploaded_at).toLocaleDateString("en-GB")}
                </p>
              </B2CPanelCardFooter>
            ) : null}
          </B2CPanelCard>
        );
      }}
    </AsyncBoundary>
  );
}

function Upload({
  onUploaded,
  onSettled,
}: {
  onUploaded: () => void;
  onSettled: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) {
      setFile(accepted[0]);
      setError(null);
      setDone(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxSize: MAX_BYTES,
    multiple: false,
  });

  // Say which rule rejected the file. "Upload failed" for a 12MB PDF sends
  // somebody to find a smaller file when what they needed was to compress it.
  useEffect(() => {
    const rejection = fileRejections[0];
    if (!rejection) return;
    const code = rejection.errors[0]?.code;
    setError(
      code === "file-too-large"
        ? "That file is larger than 10MB."
        : code === "file-invalid-type"
          ? "Only a PDF can be read."
          : "We could not take that file.",
    );
  }, [fileRejections]);

  const send = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadCv(file);
      setDone(true);
      setFile(null);
      onUploaded();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
      onSettled();
    }
  };

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-panel border border-dashed p-6 text-center transition-colors ${
          isDragActive ? "bg-osce-accent-muted" : "bg-osce-surface hover:bg-osce-surface-alt"
        }`}
      >
        <input {...getInputProps()} />
        <HiOutlineCloudArrowUp className="mx-auto h-7 w-7 text-b2c-text-muted" />
        <p className="mt-2 text-osce-body font-medium text-osce-ink-900">
          {file ? file.name : isDragActive ? "Drop the PDF here" : "Drop your CV, or click to choose"}
        </p>
        <p className="mt-1 text-osce-meta text-b2c-text-muted">A PDF, up to 10MB.</p>
      </div>

      {error ? <Alert tone="danger">{error}</Alert> : null}
      {done ? (
        <p role="status" className="text-osce-meta text-osce-success">
          CV received. We will read it into the sections below in about a minute.
        </p>
      ) : null}

      {file ? (
        <div className="flex items-center justify-end gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setFile(null);
              setError(null);
            }}
          >
            <HiOutlineXMark className="h-4 w-4" /> Discard
          </Button>
          <Button size="sm" onClick={() => void send()} disabled={busy}>
            {busy ? "Uploading…" : "Upload CV"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function Sections({ structured }: { structured: StructuredCv }) {
  const filled = SECTIONS.filter((section) => structured[section.key]);
  if (filled.length === 0) {
    return (
      <p className="mt-4 text-osce-meta text-b2c-text-muted">
        Nothing has been read from this CV yet.
      </p>
    );
  }
  return (
    <dl className="mt-5 grid gap-4 sm:grid-cols-2">
      {filled.map(({ key, title, icon: Icon }) => (
        <div key={key} className="rounded-panel border border-osce-border bg-white p-4">
          <dt className="flex items-center gap-2 text-osce-meta font-semibold uppercase tracking-wide text-b2c-text-muted">
            <Icon className="h-4 w-4" /> {title}
          </dt>
          <dd className="mt-2 whitespace-pre-wrap text-osce-body text-osce-ink-900">
            {structured[key]}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default CvPanel;
