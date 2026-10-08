import { errorMessage } from "@/foundation/hooks/useAsync";
import { PlatformError } from "@/foundation/platform-client";

/** Why one uploaded file was refused, in words that say what to do rather than the server's text. */
export function uploadFailureMessage(cause: unknown): string {
  if (cause instanceof PlatformError) {
    if (cause.code === "invalid_import_file") {
      return "It is not a PDF or Word file we can read, or it has nothing in it.";
    }
    if (cause.code === "too_many_requests") {
      return "Too many imports just now. Wait a minute and upload the rest again.";
    }
  }
  return errorMessage(cause);
}

/** The line under an import, by where it has got to. */
export function importStatusLine(status: string, templatePublished: boolean): string {
  switch (status) {
    case "drafting_template":
      return "Reading the file and drafting a template. This takes about a minute.";
    case "template_ready":
      return templatePublished
        ? "Template drafted. Review it, then create the station."
        : "Template drafted. Review it; creating the station also publishes the template.";
    case "drafting_station":
      return "Copying the file into the template. This takes about a minute.";
    case "completed":
      return "Draft station created. It is in your Stations list.";
    case "failed":
      return "Could not be imported";
    default:
      return status;
  }
}
