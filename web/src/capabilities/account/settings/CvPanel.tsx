"use client";

import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import {
  HiOutlineAcademicCap,
  HiOutlineBeaker,
  HiOutlineBriefcase,
  HiOutlineClipboardDocumentCheck,
  HiOutlineCloudArrowUp,
  HiOutlineCog8Tooth,
  HiOutlineCurrencyPound,
  HiOutlineNewspaper,
  HiOutlineTrash,
  HiOutlineUser,
  HiOutlineXMark,
} from "react-icons/hi2";
import { LuAward, LuCrown, LuPresentation, LuTrophy } from "react-icons/lu";
import type { ComponentType } from "react";
import {
  Alert,
  AsyncBoundary,
  Button,
  ConfirmModal,
  ModalHelper,
  Panel,
  Spinner,
} from "@/foundation/ui";
import { errorMessage, useAsync, useMeEvents } from "@/foundation/hooks";
import { listCvs, deleteCv, readCv, uploadCv, type CvRead, type StructuredCv } from "@/capabilities/account/api";

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
 * background job. So the panel follows that one row by its id until the job
 * settles, rather than pretending the sections are instant — the old copy told
 * people "about 60 seconds", and a screen that goes quiet for a minute reads as
 * a failed upload.
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
  const reloadList = state.reload;

  /*
   * The upload in flight, named by the id `POST /cv` answered with.
   *
   * Asking the list "is it done yet" re-reads every CV to find out something
   * about one of them, and if a second upload lands in between it can answer
   * about the wrong row. `watching` is null whenever nothing is in flight, and
   * the loader below declines to run in that case.
   */
  const [watching, setWatching] = useState<string | null>(null);
  const watched = useAsync(
    (signal) => (watching ? readCv(watching, signal) : Promise.resolve(null)),
    [watching],
  );
  const reloadWatched = watched.reload;

  // An unread answer is still an answer being waited for — the first poll has
  // not landed yet, and treating that as finished would fold the row back into
  // the list before anything had been read from it.
  const stillReading =
    watching !== null && (watched.data?.status ?? "processing") === "processing";

  useEffect(() => {
    if (watching === null) return;
    if (!stillReading) {
      // Read or refused: either way the list is the view that stays open, so
      // hand the finished row back to it and stop asking about a single id.
      setWatching(null);
      reloadList();
    }
  }, [watching, stillReading, reloadList]);
  // `run_extraction_job` publishes `cv.read` to the CV's owner when the job
  // settles, so this re-reads on that event rather than polling for it.
  useMeEvents(
    watching !== null && stillReading ? ["cv.read"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.cv_id === watching) reloadWatched();
      },
      [watching, reloadWatched],
    ),
  );

  /*
   * Offered at any status, `processing` included: the server allows it and the
   * extraction job tolerates a row that has gone. Somebody who uploaded the
   * wrong file should not have to wait for a model to finish reading a document
   * they have disowned before they are permitted to remove it.
   */
  const [confirming, setConfirming] = useState<CvRead | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteFailure, setDeleteFailure] = useState<string | null>(null);

  async function remove(cv: CvRead) {
    setDeleting(true);
    setDeleteFailure(null);
    try {
      await deleteCv(cv.id);
      setConfirming(null);
      // Stop following a row that no longer exists, then re-read the list.
      setWatching(null);
      reloadList();
    } catch (cause) {
      setDeleteFailure(errorMessage(cause));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
    <AsyncBoundary state={state}>
      {(list) => {
        // The row being followed outranks the list's newest while it lasts,
        // which is what shows the sections the moment the job writes them.
        const latest: CvRead | undefined = watched.data ?? list.cvs?.[0];
        return (
          <Panel title="Your CV">
            <div className="space-y-4">
              <ModalHelper className="mt-0">
                Upload the CV you will bring to the interview. We read it into
                sections and base your practice questions on what is in it.
              </ModalHelper>
              <Upload onUploaded={(cvId) => setWatching(cvId)} />
              {latest?.status === "processing" ? (
                <p className="flex items-center gap-2 text-osce-meta text-ink-subtle">
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
            </div>
            {latest ? (
              <div className="mt-6 flex items-center justify-between gap-3 border-t border-border pt-4">
                <p className="text-osce-meta text-ink-subtle">
                  {latest.original_filename}
                  {latest.status === "completed"
                    ? ` · uploaded ${new Date(latest.uploaded_at).toLocaleDateString("en-GB")}`
                    : null}
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="gap-2"
                  onClick={() => setConfirming(latest)}
                >
                  <HiOutlineTrash className="h-4 w-4" aria-hidden />
                  Delete
                </Button>
              </div>
            ) : null}
          </Panel>
        );
      }}
    </AsyncBoundary>
      {deleteFailure ? (
        <Alert tone="danger" className="mt-3">
          {deleteFailure}
        </Alert>
      ) : null}
      <ConfirmModal
        isOpen={confirming !== null}
        onCancel={() => {
          if (!deleting) setConfirming(null);
        }}
        onConfirm={() => {
          if (confirming) void remove(confirming);
        }}
        isLoading={deleting}
        title="Delete this CV?"
        confirmText="Delete"
        message="The file and everything read from it are removed. This cannot be undone."
      />
    </>
  );
}

function Upload({ onUploaded }: { onUploaded: (cvId: string) => void }) {
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
      // The receipt's id is what the panel follows: the row exists and is
      // `processing` here, and the sections are the job's to write later.
      const receipt = await uploadCv(file);
      setDone(true);
      setFile(null);
      onUploaded(receipt.id);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
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
        <HiOutlineCloudArrowUp className="mx-auto h-7 w-7 text-ink-subtle" />
        <p className="mt-2 text-osce-body font-medium text-ink">
          {file ? file.name : isDragActive ? "Drop the PDF here" : "Drop your CV, or click to choose"}
        </p>
        <p className="mt-1 text-osce-meta text-ink-subtle">A PDF, up to 10MB.</p>
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
      <p className="mt-4 text-osce-meta text-ink-subtle">
        Nothing has been read from this CV yet.
      </p>
    );
  }
  return (
    <dl className="mt-5 grid gap-4 sm:grid-cols-2">
      {filled.map(({ key, title, icon: Icon }) => (
        <div key={key} className="rounded-panel border border-osce-border bg-white p-4">
          <dt className="flex items-center gap-2 text-osce-meta font-semibold uppercase tracking-wide text-ink-subtle">
            <Icon className="h-4 w-4" /> {title}
          </dt>
          <dd className="mt-2 whitespace-pre-wrap text-osce-body text-ink">
            {structured[key]}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default CvPanel;
