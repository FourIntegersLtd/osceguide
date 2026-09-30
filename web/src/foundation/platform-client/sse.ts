/**
 * Reading a Server-Sent Events body that arrived over `fetch`.
 *
 * `EventSource` only speaks GET and cannot send headers, so a stream opened by
 * a POST with a body (a rubric's trial mark) is read from `response.body`
 * instead. This file is the text half of that: it turns the chunks the network
 * hands over into whole frames. It is pure, so a test can feed it bytes cut at
 * awkward places and assert the frames that come out.
 *
 * The wire format is the one `app/core/sse.py::frame` writes:
 * `event: <name>\ndata: <line>\ndata: <line>\n\n`. A frame with no `event:`
 * line is a `message`, as the SSE specification says.
 */

/** One complete event: its name and its data lines joined back together. */
export interface SseFrame {
  event: string;
  data: string;
}

/** Split accumulated text into finished frames, keeping any unfinished tail for the next chunk. */
export function createSseParser(): { push: (chunk: string) => SseFrame[] } {
  let buffer = "";

  function parseBlock(block: string): SseFrame | null {
    let eventName = "message";
    const dataLines: string[] = [];
    for (const rawLine of block.split("\n")) {
      const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
      // A line starting with a colon is a comment (a keep-alive); skip it.
      if (line === "" || line.startsWith(":")) continue;
      const colonIndex = line.indexOf(":");
      const fieldName = colonIndex === -1 ? line : line.slice(0, colonIndex);
      // One optional space after the colon belongs to the syntax, not the value.
      let value = colonIndex === -1 ? "" : line.slice(colonIndex + 1);
      if (value.startsWith(" ")) value = value.slice(1);
      if (fieldName === "event") eventName = value;
      else if (fieldName === "data") dataLines.push(value);
    }
    return dataLines.length === 0 && eventName === "message" ? null : { event: eventName, data: dataLines.join("\n") };
  }

  return {
    push(chunk: string): SseFrame[] {
      buffer += chunk.replace(/\r\n/g, "\n");
      const frames: SseFrame[] = [];
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const frame = parseBlock(buffer.slice(0, boundary));
        if (frame) frames.push(frame);
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
      }
      return frames;
    },
  };
}
