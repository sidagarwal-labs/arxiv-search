import test from "node:test";
import assert from "node:assert/strict";
import { PaperController, citationURL, createPaperTransport } from "./paper-api.js";

// Parent pytest owns the deterministic local WSGI fixture and passes its URL.
const base = process.env.PAPER_TEST_BASE_URL;

test("real local paper service: explicit prepare, open and two follow-ups", {
  skip: base ? false : "PAPER_TEST_BASE_URL is not set",
}, async () => {
  const url = new URL(base);
  assert.ok(["localhost", "127.0.0.1", "[::1]"].includes(url.hostname), "integration URL must be local");
  const calls = [];
  const fetcher = async (target, options) => {
    calls.push({ target, body: JSON.parse(options.body) });
    return fetch(target, options);
  };
  const c = new PaperController({ arxiv_id: "2510.12345" }, {
    transport: createPaperTransport({ base, fetcher }),
  });
  assert.equal(calls.length, 0);

  await c.prepare();
  assert.equal(c.error, "");
  assert.equal(c.stage, "consent");
  assert.equal(calls.length, 1);
  assert.match(calls[0].target, /\/api\/paper\/prepare$/);
  assert.deepEqual(Object.keys(calls[0].body).sort(), ["arxiv_id", "request_id"]);
  assert.equal(c.messages.length, 0);
  assert.ok(["html", "pdf", "abstract"].includes(c.paper.source));
  assert.equal(c.paper.coverage.source, c.paper.source);
  assert.ok(Array.isArray(c.paper.coverage.included_sections));
  assert.ok(c.paper.coverage.included_sections.length > 0);
  assert.ok(Array.isArray(c.paper.coverage.omitted));
  assert.ok(Array.isArray(c.paper.coverage.warnings));
  assert.equal(typeof c.paper.coverage.figures, "string");
  assert.ok(c.paper.outline.length > 0);
  for (const section of c.paper.outline) assert.ok(citationURL(section.href, c.paper), section.href);
  assert.equal(typeof c.limits.expires_at, "number");
  assert.ok(c.limits.expires_at > Date.now() / 1000);

  await c.open();
  assert.equal(c.error, "");
  assert.equal(c.stage, "ready");
  assert.equal(calls.length, 2);
  assert.match(calls[1].target, /\/api\/paper\/open$/);
  assert.deepEqual(Object.keys(calls[1].body).sort(), ["preparation", "request_id"]);
  assert.notEqual(calls[1].body.request_id, calls[0].body.request_id);
  assert.equal(c.limits.turns_left, 10);
  assert.equal(typeof c.limits.expires_at, "number");
  assert.equal(c.messages.length, 1);
  assert.equal(c.messages[0].turn_index, 0);
  assert.ok(c.messages[0].sig);
  assert.ok(Array.isArray(c.suggested_questions) && c.suggested_questions.length > 0);
  const overview = c.messages[0].content;

  // Invalid local input must not issue a request.
  await c.ask(" ".repeat(10));
  await c.ask("x".repeat(501));
  assert.equal(calls.length, 2);

  await c.ask("What method is described?");
  assert.equal(c.error, "");
  assert.equal(calls.length, 3);
  assert.match(calls[2].target, /\/api\/paper\/chat$/);
  assert.deepEqual(Object.keys(calls[2].body).sort(), ["messages", "question", "request_id", "session"]);
  assert.deepEqual(calls[2].body.messages, [{
    role: "assistant", content: overview, sig: c.messages[0].sig, turn_index: 0,
  }]);
  assert.equal(c.limits.turns_left, 9);
  assert.equal(c.messages.at(-1).content, "The abstract describes a method. [abstract]");
  assert.equal(c.messages.at(-1).turn_index, 1);
  assert.ok(c.messages.at(-1).sig);
  assert.equal(typeof c.memory, "object");
  assert.notEqual(c.memory, null);
  for (const citation of c.messages.at(-1).citations) assert.ok(citationURL(citation.href, c.paper), citation.href);

  await c.ask("What does it conclude?");
  assert.equal(c.error, "");
  assert.equal(calls.length, 4);
  assert.notEqual(calls[3].body.request_id, calls[2].body.request_id);
  assert.deepEqual(calls[3].body.messages, [
    calls[2].body.messages[0],
    { role: "user", content: "What method is described?" },
    {
      role: "assistant", content: "The abstract describes a method. [abstract]",
      sig: c.messages[2].sig, turn_index: 1,
    },
  ]);
  for (const message of calls[3].body.messages) {
    assert.deepEqual(Object.keys(message).sort(), message.role === "assistant"
      ? ["content", "role", "sig", "turn_index"] : ["content", "role"]);
  }
  assert.equal(c.limits.turns_left, 8);
  assert.equal(c.messages.at(-1).turn_index, 2);
  assert.ok(c.messages.at(-1).sig);
  assert.equal(typeof c.memory, "object");
  assert.notEqual(c.memory, null);
  assert.equal(c.pending, null);
  assert.equal(calls.length, 4);
});
