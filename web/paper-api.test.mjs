import test from "node:test";
import assert from "node:assert/strict";
import { PaperController, PaperConversation, citationURL, createPaperTransport } from "./paper-api.js";
import { pdfURL, sourceURL } from "./paper-reader.js";

test("reader URLs only allow modern corpus identities and positive integer revisions", () => {
  assert.equal(pdfURL({ arxiv_id: "2510.00202" }), "https://arxiv.org/pdf/2510.00202");
  assert.equal(pdfURL({ arxiv_id: "2510.00202", version: 3 }), "https://arxiv.org/pdf/2510.00202v3");
  assert.equal(sourceURL({ arxiv_id: "2510.00202", version: 3 }), "https://arxiv.org/abs/2510.00202v3");
  for (const arxiv_id of ["interface-demo", "../test", "https://evil.test", "2510.00202?x=1", "2510.00202v3"]) {
    assert.equal(pdfURL({ arxiv_id }), null);
  }
  for (const version of [0, -1, 1.5, "3", Infinity]) {
    assert.equal(pdfURL({ arxiv_id: "2510.00202", version }), null);
  }
});

const paper = {
  arxiv_id: "2510.00027", version: 2, source: "html", title: "Test paper",
  coverage: { source: "html", included_sections: [{ id: "S1", label: "Methods" }],
    omitted: [{ id: "bib", label: "References", reason: "references" }],
    warnings: ["conversion warning"], figures: "captions_only", equations: "text_or_latex" },
  outline: [{ id: "S1", label: "Methods", href: "https://arxiv.org/html/2510.00027v2#S1" }],
};
const limits = { turns_left: 10, expires_at: 2000000000 };
const overview = {
  text: "Full signed overview.\nIncluding every paragraph.", grounded: true,
  citations: paper.outline, suggested_questions: ["What changed?"],
  assistant_sig: "overview-signature", turn_index: 0,
};
function response(operation, body) {
  if (operation === "prepare") return {
    preparation: "prepared", paper, overview_cache: "hit", consent_required: true,
    limits: { expires_at: limits.expires_at },
  };
  if (operation === "context") return { paper };
  if (operation === "ask") return {
    answer: `Answer to ${body.question} [S1] and [missing].\n\nSecond paragraph.`,
    grounded: body.history.length > 0, citations: paper.outline, paper, memory: {},
  };
  if (operation === "open") return { session: "session", paper, overview, limits, cache: { overview: "hit" } };
  return {
    answer: `Answer to ${body.question}`, grounded: false, citations: paper.outline,
    assistant_sig: "signature-" + body.request_id, turn_index: 1,
    limits: { ...limits, turns_left: 6 }, memory: { truncated: true },
  };
}
function answerText(question) {
  return `Answer to ${question} [S1] and [missing].\n\nSecond paragraph.`;
}
function fixture(transport) {
  const calls = [];
  let next = 0;
  const controller = new PaperController(paper, {
    now: () => 1800000000000, requestId: () => `request-${++next}`,
    transport: async (operation, body) => {
      calls.push({ operation, body: structuredClone(body) });
      return transport ? transport(operation, body) : response(operation, body);
    },
  });
  return { controller, calls };
}
async function ready(c) { await c.prepare(); await c.open(); }

test("construction and workspace state are inert; preparation requires separate consent click", async () => {
  const { controller: c, calls } = fixture();
  assert.equal(calls.length, 0);
  await c.open();
  await c.ask("No consent");
  assert.equal(calls.length, 0);
  await c.prepare();
  assert.equal(c.stage, "consent");
  assert.equal(c.messages.length, 0);
  assert.deepEqual(calls[0], { operation: "prepare", body: { arxiv_id: paper.arxiv_id, request_id: "request-1" } });
  await c.prepare();
  assert.equal(calls.length, 1);
  await c.open();
  assert.deepEqual(calls[1].body, { preparation: "prepared", request_id: "request-2" });
  assert.equal(c.messages[0].content, overview.text);
});

test("chat sends full signed baseline and complete exchanges; server turns and limits win", async () => {
  const { controller: c, calls } = fixture();
  await ready(c);
  await c.ask("First?");
  assert.deepEqual(calls[2].body.messages, [{
    role: "assistant", content: overview.text, sig: overview.assistant_sig, turn_index: 0,
  }]);
  assert.equal(c.messages[2].turn_index, 1);
  assert.equal(c.limits.turns_left, 6);
  await c.ask("Second?");
  assert.deepEqual(calls[3].body.messages, [
    calls[2].body.messages[0], { role: "user", content: "First?" },
    { role: "assistant", content: "Answer to First?", sig: "signature-request-3", turn_index: 1 },
  ]);
  // The repeated server turn is rejected, not locally renumbered.
  assert.equal(c.messages.length, 3);
  assert.ok(c.pending);
});

test("unknown failure has no automatic retry or new ID; explicit retry is byte-equivalent", async () => {
  let fail = true;
  const { controller: c, calls } = fixture((op, body) => {
    if (fail) throw new Error("Connection interrupted");
    return response(op, body);
  });
  await c.prepare();
  assert.equal(calls.length, 1);
  await c.prepare();
  await c.open();
  assert.equal(calls.length, 1);
  fail = false;
  await c.retry();
  assert.deepEqual(calls[0], calls[1]);
  assert.equal(c.stage, "consent");
});

test("session_busy retains pending question and explicitly retries same ID", async () => {
  let busy = true;
  const { controller: c, calls } = fixture((op, body) => {
    if (op === "chat" && busy) throw Object.assign(new Error("Busy"), { code: "session_busy", limits });
    return response(op, body);
  });
  await ready(c);
  await c.ask("Pending");
  assert.match(c.error, /session is busy/);
  assert.equal(c.messages.length, 1);
  await c.ask("Must not issue");
  assert.equal(calls.length, 3);
  busy = false;
  await c.retry();
  assert.deepEqual(calls[2], calls[3]);
  assert.equal(c.messages.at(-2).content, "Pending");
});

test("chat already_completed is nonrecoverable and blocks even manual replay", async () => {
  const { controller: c, calls } = fixture((op, body) => {
    if (op === "chat") throw Object.assign(new Error("Done"), { code: "already_completed" });
    return response(op, body);
  });
  await ready(c);
  await c.ask("Lost?");
  assert.equal(c.stage, "blocked");
  assert.match(c.error, /cannot be recovered/);
  await c.retry();
  await c.ask("Again?");
  await c.prepare();
  assert.equal(calls.length, 3);
});

test("known prepare errors close the ID; only an explicit new preparation gets a new ID", async () => {
  for (const code of ["already_completed", "paper_unavailable", "upstream_timeout", "budget_exhausted"]) {
    let fail = true;
    const { controller: c, calls } = fixture((op, body) => {
      if (fail) throw Object.assign(new Error("Server said no"), { code });
      return response(op, body);
    });
    await c.prepare();
    assert.equal(c.pending, null, code);
    assert.equal(c.stage, "idle", code);
    assert.match(c.error, /not refunded/);
    await c.retry();
    await c.open();
    assert.equal(calls.length, 1, code);
    fail = false;
    await c.prepare();
    assert.equal(calls.length, 2, code);
    assert.notEqual(calls[1].body.request_id, calls[0].body.request_id, code);
    assert.equal(c.stage, "consent", code);
  }
});

test("expired preparation allows explicit new preparation, not reopen", async () => {
  const { controller: c, calls } = fixture((op, body) => {
    if (op === "open") throw Object.assign(new Error("Expired"), { code: "preparation_expired" });
    return response(op, body);
  });
  await ready(c);
  assert.equal(c.stage, "idle");
  await c.retry();
  assert.equal(calls.length, 2);
  await c.prepare();
  assert.equal(calls.length, 3);
  assert.equal(calls[2].operation, "prepare");
  const { controller: local, calls: localCalls } = fixture();
  await local.prepare();
  local.now = () => limits.expires_at * 1000;
  await local.open();
  assert.equal(localCalls.length, 1);
  assert.equal(local.canPrepare, true);
  await local.prepare();
  assert.notEqual(localCalls[1].body.request_id, localCalls[0].body.request_id);
});

test("model_invalid_answer consumes chat turn, applies top-level limits, permits only a new question", async () => {
  let invalid = true;
  const { controller: c, calls } = fixture((op, body) => {
    if (op === "chat" && invalid) {
      throw Object.assign(new Error("Invalid"), { code: "model_invalid_answer", limits: { ...limits, turns_left: 9 } });
    }
    return response(op, body);
  });
  await ready(c);
  await c.ask("Rejected?");
  assert.equal(c.pending, null);
  assert.equal(c.limits.turns_left, 9);
  assert.equal(c.messages.length, 1);
  await c.retry();
  assert.equal(calls.length, 3);
  invalid = false;
  await c.ask("New question");
  assert.notEqual(calls[3].body.request_id, calls[2].body.request_id);
  assert.deepEqual(calls[3].body.messages, calls[2].body.messages);
  assert.equal(c.messages.at(-2).content, "New question");
});

test("overview validation failure is terminal and cannot open another session", async () => {
  const { controller: c, calls } = fixture((op, body) => {
    if (op === "open") throw Object.assign(new Error("Invalid"), { code: "model_invalid_answer" });
    return response(op, body);
  });
  await ready(c);
  assert.equal(c.stage, "blocked");
  await c.retry();
  await c.open();
  assert.equal(calls.length, 2);
});

test("outcome_unknown leaves same pending body as the only possible retry", async () => {
  let unknown = true;
  const { controller: c, calls } = fixture((op, body) => {
    if (op === "chat" && unknown) throw Object.assign(new Error("Pending"), { code: "outcome_unknown" });
    return response(op, body);
  });
  await ready(c);
  await c.ask("Maybe?");
  await c.ask("Different ID?");
  assert.equal(calls.length, 3);
  unknown = false;
  await c.retry();
  assert.deepEqual(calls[3], calls[2]);
});

test("deterministic loader failures block retry and reprepare", async () => {
  for (const code of ["bad_request", "not_in_corpus"]) {
    const { controller: c, calls } = fixture(() => { throw Object.assign(new Error("Loader failed"), { code }); });
    await c.prepare();
    assert.equal(c.stage, "blocked", code);
    await c.retry();
    await c.prepare();
    assert.equal(calls.length, 1, code);
  }
});

test("double clicks and overlapping submissions issue exactly one operation", async () => {
  let release;
  const { controller: c, calls } = fixture((op, body) =>
    new Promise(resolve => { release = () => resolve(response(op, body)); }));
  const work = c.prepare();
  await c.prepare();
  await c.retry();
  assert.equal(calls.length, 1);
  release();
  await work;
});

test("clear deletes history and credentials without resetting server quota or renewing", async () => {
  const { controller: c, calls } = fixture();
  await ready(c);
  await c.ask("Question");
  c.draft = "Private draft";
  c.clear();
  assert.deepEqual(c.messages, []);
  assert.equal(c.draft, "");
  assert.equal(c.session, null);
  assert.equal(c.pending, null);
  assert.equal(c.memory, null);
  assert.equal(c.limits.turns_left, 6);
  await c.prepare();
  await c.open();
  await c.ask("Renew?");
  await c.retry();
  assert.equal(calls.length, 3);
});

test("expiry keeps transcript and disallows requests; zero server allowance also disables composer", async () => {
  const { controller: c, calls } = fixture();
  await ready(c);
  const saved = structuredClone(c.messages);
  c.now = () => limits.expires_at * 1000;
  assert.equal(c.expired, true);
  assert.equal(c.canAsk, false);
  await c.ask("Expired");
  assert.deepEqual(c.messages, saved);
  assert.equal(calls.length, 2);
  c.now = () => 0;
  c.limits = { ...limits, turns_left: 0 };
  assert.equal(c.canAsk, false);
});

test("malformed replies retain request and reject missing overview signatures", async () => {
  const { controller: c } = fixture((op, body) => {
    const data = response(op, body);
    return op === "open" ? { ...data, overview: { ...overview, assistant_sig: "" } } : data;
  });
  await ready(c);
  assert.equal(c.messages.length, 0);
  assert.equal(c.pending.operation, "open");
  assert.equal(c.canAsk, false);
});

test("exact arXiv source, version, host, path and locator validation", () => {
  const valid = paper.outline[0].href;
  assert.equal(citationURL(valid, paper), valid);
  for (const bad of [
    valid.replace("https:", "http:"), valid.replace("arxiv.org", "arxiv.org.evil.test"),
    valid.replace("arxiv.org", "evil.test@arxiv.org"), valid.replace("v2", "v3"),
    valid.replace("/html/", "/abs/"), valid + "?redirect=evil",
    valid.replace("#S1", "/../2510.00028v2#S1"), valid.replace("#S1", "#<script>"),
    valid.replace("arxiv.org", "arxiv.org:443"), "javascript:alert(1)",
    valid.replace("/html/", "//html/"), valid.replace("#S1", "%23S1"),
  ]) assert.equal(citationURL(bad, paper), null, bad);
  const pdf = { ...paper, source: "pdf" };
  assert.ok(citationURL("https://arxiv.org/pdf/2510.00027v2#page=3", pdf));
  assert.equal(citationURL("https://arxiv.org/pdf/2510.00027v2#S3", pdf), null);
  assert.equal(citationURL("https://arxiv.org/pdf/2510.00027v2#page=0", pdf), null);
  assert.ok(citationURL("https://arxiv.org/abs/2510.00027v2", { ...paper, source: "abstract" }));
});

test("injected HTTP adapter preserves exact POST contract and error limits", async () => {
  let captured;
  const transport = createPaperTransport({ base: "https://offline.invalid/", fetcher: async (...args) => {
    captured = args;
    return { ok: false, json: async () => ({
      error: { code: "session_busy", message: "Busy" }, limits,
    }) };
  } });
  await assert.rejects(transport("chat", { request_id: "fixed" }), error =>
    error.code === "session_busy" && error.limits === limits);
  assert.equal(captured[0], "https://offline.invalid/api/paper/chat");
  assert.equal(captured[1].method, "POST");
  assert.equal(captured[1].body, '{"request_id":"fixed"}');
});

test("DOM wiring: demo when disabled; live mode loads context on open and asks without consent", async (t) => {
  class Element {
    constructor() {
      this.children = []; this.events = {}; this.hidden = false; this.value = "";
      this.dataset = {};
      this.attributes = {};
      this.scrollTop = 0;
      this.classList = { add() {}, remove() {}, toggle() {} };
    }
    set innerHTML(_) { throw new Error("Untrusted HTML rendering forbidden"); }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    addEventListener(name, callback) { this.events[name] = callback; }
    setAttribute(name, value) { this.attributes[name] = value; }
    removeAttribute(name) { delete this.attributes[name]; }
    focus() {}
    scrollIntoView() {}
  }
  const nodes = new Map();
  const $ = selector => {
    if (!nodes.has(selector)) nodes.set(selector, new Element());
    return nodes.get(selector);
  };
  const previous = {};
  for (const key of ["document", "window", "location", "fetch", "setInterval"]) previous[key] = globalThis[key];
  t.after(() => Object.assign(globalThis, previous));
  globalThis.document = {
    querySelector: $, createElement: () => new Element(),
    body: new Element(), addEventListener() {},
  };
  globalThis.window = { scrollY: 0, scrollTo() {} };
  globalThis.location = { hostname: "localhost", search: "?api=https://never.invalid&mock=1" };
  globalThis.setInterval = () => 0;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    const operation = url.split("/").at(-1);
    const body = JSON.parse(options.body);
    calls.push({ operation, body });
    return { ok: true, json: async () => response(operation, body) };
  };
  $("#paper-workspace").hidden = true;
  const { CONFIG } = await import("./config.js");
  const { openPaper, closePaper, previewPaperChat } = await import("./paper-chat.js");
  const enabled = CONFIG.PAPER_API_ENABLED;
  t.after(() => { CONFIG.PAPER_API_ENABLED = enabled; });
  CONFIG.PAPER_API_ENABLED = false;
  assert.equal(calls.length, 0);
  openPaper({ ...paper, arxiv_id: "2510.00028" });
  assert.equal($("#paper-mode").textContent, "Preview");
  assert.equal(calls.length, 0);
  const toolbar = $("#paper-reader-body").children[0];
  assert.match(toolbar.children[0].textContent, /AI not connected/);
  assert.equal(toolbar.children[1].href, "https://arxiv.org/pdf/2510.00028v2");
  const details = $("#paper-reader-body").children[1];
  assert.equal(details.open, undefined);
  assert.match(details.children[1].textContent, /AI coverage: none/);
  const frame = $("#paper-reader-body").children.find(node => node.src);
  assert.equal(frame.src, "https://arxiv.org/pdf/2510.00028v2");
  assert.equal(frame.referrerPolicy, "no-referrer");
  assert.equal($("#paper-workspace").attributes["data-view"], "read");
  $("#paper-discuss-tab").events.click();
  assert.equal($("#paper-workspace").attributes["data-view"], "discuss");
  $("#paper-read-tab").events.click();
  $("#paper-viewer-toggle").events.click();
  assert.match($("#paper-reader-body").children.at(-1).textContent, /viewer unavailable/);
  assert.equal($("#paper-reader-body").children.some(node => node.src), false);
  assert.equal(calls.length, 0);
  $("#paper-viewer-toggle").events.click();
  assert.equal($("#paper-reader-body").children.at(-1).src, frame.src);
  // No start buttons: shortcuts visible but inert, composer disabled, no network.
  assert.equal($("#paper-transcript").children.length, 1);
  assert.equal($("#paper-transcript").children[0].children.some(node => node.events?.click), false);
  assert.match($("#paper-transcript").children[0].children.at(-1).textContent, /not connected/);
  const chips = $("#paper-suggestions").children;
  assert.equal(chips.length, 5);
  assert.equal(chips[0].textContent, "Summarize this paper");
  assert.ok(chips.every(chip => chip.disabled));
  assert.equal($("#paper-suggestions").hidden, false);
  assert.equal($("#paper-question").disabled, true);
  $("#paper-question").value = "Ignored";
  $("#paper-form").events.submit({ preventDefault() {} });
  assert.equal($("#paper-transcript").children.length, 1);
  $("#paper-question").value = "";
  assert.equal(calls.length, 0);
  $("#paper-reader-body").scrollTop = 137;
  closePaper();
  openPaper({ ...paper, arxiv_id: "2510.00028" });
  assert.equal($("#paper-reader-body").scrollTop, 137);
  closePaper();
  CONFIG.PAPER_API_ENABLED = true;
  const tick = () => new Promise(resolve => setImmediate(resolve));
  openPaper(paper);
  assert.equal($("#paper-mode").textContent, "AI");
  assert.match($("#paper-disclosure").children[0].textContent, /Reading the paper/);
  await tick();
  assert.deepEqual(calls[0], { operation: "context", body: { arxiv_id: paper.arxiv_id } });
  assert.match($("#paper-disclosure").children[0].textContent, /full text \(v2\)/);
  assert.match($("#paper-disclosure").children[1].textContent, /Methods/);
  assert.match($("#paper-disclosure").children[2].textContent, /References/);
  assert.match($("#paper-reader-body").children[0].children[0].textContent, /Discuss/);
  assert.equal($("#paper-question").disabled, false);
  assert.equal($("#paper-suggestions").hidden, false);
  assert.ok($("#paper-suggestions").children.every(chip => !chip.disabled));
  $("#paper-suggestions").events.click({ target: { closest: () => ({ textContent: "What are the limitations?", disabled: false }) } });
  assert.match($("#paper-transcript").children.at(-1).children[1].children.at(-1), /Reading the paper/);
  await tick();
  assert.deepEqual(calls[1].body, { arxiv_id: paper.arxiv_id, question: "What are the limitations?", history: [] });
  const answer = $("#paper-transcript").children[1];
  assert.equal(answer.children.length, 4);
  const chip = answer.children[1].children[1];
  assert.equal(chip.textContent, "Methods");
  assert.equal(chip.href, paper.outline[0].href);
  assert.match(answer.children[1].children[2], /\[missing\]/);
  assert.match(answer.children[3].textContent, /Not clearly answered/);
  assert.equal($("#paper-suggestions").hidden, true);
  assert.match($("#paper-help").textContent, /9 of 10 questions left/);
  $("#paper-question").value = "Follow up";
  $("#paper-form").events.submit({ preventDefault() {} });
  await tick();
  assert.deepEqual(calls[2].body.history, [{ user: "What are the limitations?", assistant: answerText("What are the limitations?") }]);
  assert.equal($("#paper-transcript").children.length, 4);
  closePaper();
  openPaper(paper);
  assert.equal(calls.length, 3);
  assert.equal($("#paper-transcript").children.length, 4);
  $("#paper-clear").events.click();
  assert.equal($("#paper-transcript").children.length, 1);
  assert.equal($("#paper-suggestions").hidden, false);
  closePaper();
  previewPaperChat();
  assert.equal($("#paper-mode").textContent, "Preview");
  assert.equal($("#paper-suggestions").children.length, 5);
  assert.equal($("#paper-reader-body").children.some(node => node.src), false);
  assert.equal(calls.length, 3);
});

test("live conversation: errors keep the question for retry, limit is 10, invalid context is an error", async () => {
  let fail = true;
  const calls = [];
  const c = new PaperConversation(paper, { transport: async (operation, body) => {
    calls.push(operation);
    if (operation === "context") return { paper: { ...paper, arxiv_id: "other" } };
    if (fail) throw Object.assign(new Error("x"), { code: "budget_exhausted" });
    return response(operation, body);
  } });
  await c.loadContext();
  assert.equal(c.contextState, "error");
  await c.ask("  Why?  ");
  assert.match(c.error, /midnight UTC/);
  assert.equal(c.failedQuestion, "Why?");
  assert.equal(c.messages.length, 0);
  fail = false;
  await c.retry();
  assert.equal(c.messages.length, 1);
  assert.equal(c.error, "");
  await c.ask("x".repeat(501));
  for (let i = 0; i < 12; i++) await c.ask(`Q${i}`);
  assert.equal(c.messages.length, 10);
  assert.equal(c.canAsk, false);
  assert.equal(calls.filter(op => op === "ask").length, 11);
});