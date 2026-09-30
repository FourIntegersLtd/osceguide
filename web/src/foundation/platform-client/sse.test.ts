import assert from "node:assert/strict";
import { test } from "node:test";
import { createSseParser } from "@/foundation/platform-client/sse";

test("frames split across chunks come out whole, in order", () => {
  const parser = createSseParser();
  assert.deepEqual(parser.push('event: connected\ndata: {}\n\nevent: snap'), [{ event: "connected", data: "{}" }]);
  assert.deepEqual(parser.push('shot\ndata: {"status":"marking"}\n'), []);
  assert.deepEqual(parser.push("\n"), [{ event: "snapshot", data: '{"status":"marking"}' }]);
});

test("several data lines join with a newline, and comments are skipped", () => {
  const parser = createSseParser();
  assert.deepEqual(parser.push(": keep-alive\n\nevent: snapshot\r\ndata: line one\r\ndata: line two\r\n\r\n"), [
    { event: "snapshot", data: "line one\nline two" },
  ]);
});

test("a frame with no event name is a message", () => {
  const parser = createSseParser();
  assert.deepEqual(parser.push("data: hello\n\n"), [{ event: "message", data: "hello" }]);
});
