import type { Transcript } from "@/capabilities/attempt-runner/api";

/**
 * A consultation as a document.
 *
 * There is no download route and there does not need to be: the transcript is
 * already in the page by the time anybody can ask for a copy, so a copy is a
 * formatting question rather than a fetch. Keeping the formatting in one place
 * matters because two screens offer it — the candidate reading back their own
 * station, and the examiner marking somebody else's — and a transcript that
 * prints differently depending on who saved it is a transcript nobody trusts.
 *
 * The speaker words are the product's, not the API's: the wire carries `user`
 * for the person being examined and everything else for the simulated patient.
 */

/** Who said it, in the words both screens already use. */
export function speakerOf(role: string): string {
  return role === "user" ? "Doctor" : "Patient";
}

/** The transcript as plain text: one turn per paragraph, speaker first. */
export function transcriptAsText(transcript: Transcript): string {
  return transcript.messages
    .map((message) => `${speakerOf(message.role)}: ${message.message}`)
    .join("\n\n");
}

/**
 * Save the transcript to a file.
 *
 * A blob and a synthetic anchor rather than a link to an API route, because the
 * bytes are local and a route would be a second copy of the same document with
 * its own authorisation question to get right. The caller names the file: the
 * examiner's copy wants to say which attempt it came from, and the candidate's
 * does not.
 */
export function downloadTranscript(transcript: Transcript, filename = "transcript.txt"): void {
  const url = URL.createObjectURL(
    new Blob([transcriptAsText(transcript)], { type: "text/plain;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  // Revoked after the click rather than in a timeout: the anchor is never
  // appended to the document, so nothing else can still be reading the URL.
  URL.revokeObjectURL(url);
}
