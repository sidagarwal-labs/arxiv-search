// No storage, startup requests, automatic retries, or search-client coupling.
export function createPaperTransport({ base = "", fetcher = globalThis.fetch } = {}) {
  return async (operation, body) => {
    const response = await fetcher(`${base.replace(/\/$/, "")}/api/paper/${operation}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), signal: AbortSignal.timeout(150000),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !data) {
      const error = new Error(data?.error?.message || "Paper request outcome is unknown.");
      error.code = data?.error?.code || "outcome_unknown";
      error.limits = data?.error?.limits ?? data?.limits;
      throw error;
    }
    return data;
  };
}

export function citationURL(href, paper) {
  const id = paper?.arxiv_id;
  if (!/^\d{4}\.\d{4,5}$/.test(id) || !Number.isInteger(paper.version) || paper.version < 1) return null;
  const version = `${id}v${paper.version}`;
  const prefix = `https://arxiv.org/${paper.source === "abstract" ? "abs" : paper.source}/${version}`;
  if (typeof href !== "string" || !href.startsWith(prefix)) return null;
  const suffix = href.slice(prefix.length);
  if (paper.source === "html" && !/^#[A-Za-z][A-Za-z0-9_.:-]{0,127}$/.test(suffix)) return null;
  if (paper.source === "pdf" && !/^#page=[1-9]\d*$/.test(suffix)) return null;
  if (paper.source === "abstract" && suffix !== "") return null;
  if (!["html", "pdf", "abstract"].includes(paper.source)) return null;
  try {
    const url = new URL(href);
    return url.protocol === "https:" && url.hostname === "arxiv.org" &&
      !url.port && !url.username && !url.password && !url.search ? href : null;
  } catch { return null; }
}

function signedReply(reply, contentKey, overview = false) {
  if (typeof reply?.[contentKey] !== "string" || !reply[contentKey].trim() ||
      typeof reply.assistant_sig !== "string" || !reply.assistant_sig ||
      !Number.isInteger(reply.turn_index) || reply.turn_index < 0 ||
      (overview && reply.turn_index !== 0) || typeof reply.grounded !== "boolean" ||
      !Array.isArray(reply.citations)) throw new Error("Invalid signed paper response.");
  return {
    role: "assistant", content: reply[contentKey], sig: reply.assistant_sig,
    turn_index: reply.turn_index, grounded: reply.grounded, citations: reply.citations,
  };
}

// paper_unavailable also covers transient extractor gaps, so it permits an explicit new prepare.
const DETERMINISTIC_PREPARE = new Set(["bad_request", "not_in_corpus"]);

export class PaperController {
  constructor(paper, { transport, requestId = () => globalThis.crypto.randomUUID(), now = () => Date.now() } = {}) {
    this.paper = paper;
    this.transport = transport;
    this.requestId = requestId;
    this.now = now;
    this.messages = [];
    this.limits = {};
    this.stage = "idle";
    this.busy = false;
    this.error = "";
    this.pending = null;
    this.draft = "";
  }

  get expired() {
    const expiry = this.limits.expires_at;
    return expiry != null && Number(expiry) * 1000 <= this.now();
  }

  get canAsk() {
    return this.stage === "ready" && !this.busy && !this.pending && !this.expired &&
      Number.isInteger(this.limits.turns_left) && this.limits.turns_left > 0;
  }

  get canPrepare() {
    return !this.pending && !this.busy &&
      (this.stage === "idle" || (this.stage === "consent" && this.expired));
  }

  prepare() {
    if (!this.canPrepare) return Promise.resolve();
    // A fresh preparation always gets a fresh request ID; the old one is never replayed.
    this.stage = "idle";
    this.preparation = null;
    return this.run("prepare", { arxiv_id: this.paper.arxiv_id });
  }

  open() {
    if (this.stage !== "consent" || this.pending || this.busy || this.expired) return Promise.resolve();
    return this.run("open", { preparation: this.preparation });
  }

  ask(question) {
    if (!this.canAsk || !question.trim() || question.trim().length > 500) return Promise.resolve();
    return this.run("chat", {
      session: this.session,
      messages: this.messages.map(({ role, content, sig, turn_index }) =>
        role === "assistant" ? { role, content, sig, turn_index } : { role, content }),
      question: question.trim(),
    });
  }

  retry() {
    if (!this.pending || this.busy || this.stage === "blocked" || this.expired) return Promise.resolve();
    return this.run(this.pending.operation, this.pending.body);
  }

  clear() {
    if (this.busy) return;
    this.messages = [];
    this.draft = "";
    this.pending = null;
    this.session = null;
    this.preparation = null;
    this.memory = null;
    this.suggested_questions = [];
    this.stage = "cleared";
    this.error = "History deleted in this tab. The server allowance was not reset; this workspace cannot silently start a new session.";
  }

  async run(operation, body) {
    if (this.busy || ["blocked", "cleared"].includes(this.stage)) return;
    if (!this.pending) this.pending = { operation, body: { ...body, request_id: this.requestId() } };
    const pending = this.pending;
    this.busy = true;
    this.error = "";
    try {
      // Keep exactly this body and ID after ambiguous failures, including malformed replies.
      const data = await this.transport(pending.operation, pending.body);
      if (!data?.limits || !Number.isFinite(data.limits.expires_at)) throw new Error("Missing paper expiry.");
      if (operation === "prepare") {
        if (!data.preparation || data.consent_required !== true || !data.paper?.coverage ||
            !Array.isArray(data.paper.outline) || data.paper.arxiv_id !== this.paper.arxiv_id) {
          throw new Error("Invalid paper preparation.");
        }
        this.preparation = data.preparation;
        this.paper = data.paper;
        this.overview_cache = data.overview_cache;
        this.stage = "consent";
      } else if (operation === "open") {
        const reply = signedReply(data.overview, "text", true);
        if (!data.session || data.paper?.arxiv_id !== this.paper.arxiv_id ||
            data.paper.version !== this.paper.version || data.paper.source !== this.paper.source ||
            !Number.isInteger(data.limits.turns_left)) throw new Error("Invalid paper session.");
        this.session = data.session;
        this.paper = data.paper;
        this.messages = [reply];
        this.suggested_questions = data.overview.suggested_questions ?? [];
        this.cache = data.cache;
        this.stage = "ready";
      } else {
        const reply = signedReply(data, "answer");
        const previous = this.messages.at(-1)?.turn_index ?? 0;
        if (reply.turn_index <= previous || !Number.isInteger(data.limits.turns_left)) {
          throw new Error("Invalid server turn or limits.");
        }
        this.messages.push({ role: "user", content: pending.body.question }, reply);
        this.memory = data.memory;
        this.draft = "";
      }
      this.limits = data.limits;
      this.pending = null;
    } catch (error) {
      if (error.limits) this.limits = error.limits;
      const code = error.code || "outcome_unknown";
      const explanations = {
        already_completed: "This request already completed, but its original response is unavailable. It cannot be recovered or replayed here. No new request will be issued.",
        session_busy: "The session is busy. Wait, then explicitly retry the same request; no new request ID will be created.",
        outcome_unknown: "The request may have completed or reserved allowance. No automatic retry or new request ID will be issued. You may explicitly retry the same request.",
      };
      const known = typeof error.code === "string" && error.code !== "outcome_unknown";
      if (operation === "prepare" && known) {
        // The server closed this request ID; a same-ID retry would only return already_completed.
        this.pending = null;
        if (DETERMINISTIC_PREPARE.has(code)) {
          this.stage = "blocked";
          this.error = `${error.message || "This paper cannot be prepared."} Preparing again would fail the same way.`;
        } else {
          this.stage = "idle";
          this.error = `${error.message || "Preparation failed."} Allowance used by the failed preparation is not refunded. Preparing again is a new, explicit request.`;
        }
        return;
      }
      if (operation === "open" && code === "preparation_expired") {
        this.pending = null;
        this.preparation = null;
        this.stage = "idle";
        this.error = "This preparation expired before opening. Preparing again is a new, explicit request.";
        return;
      }
      if (code === "model_invalid_answer" && operation === "chat") {
        // The server consumed and terminally closed this request; only a new explicit question may follow.
        this.pending = null;
        this.error = "The answer failed validation and that question's turn remains used. You may ask a new question.";
        return;
      }
      this.error = explanations[code] || `${error.message || "Paper request failed."} No automatic retry; any explicit retry uses the same request ID.`;
      if (["already_completed", "session_expired", "preparation_expired", "context_changed", "model_invalid_answer",
        "turn_limit", "transcript_invalid", "invalid_history", "bad_request"].includes(code)) this.stage = "blocked";
    } finally {
      this.busy = false;
    }
  }
}

// Live paper chat: context loads automatically (no model call); the first question
// starts the conversation. History stays in this tab and is sent with each question.
export const PAPER_QUESTION_LIMIT = 10;

const PAPER_ERRORS = {
  budget_exhausted: "Today's AI budget is used up. Paper chat returns after midnight UTC.",
  upstream_unavailable: "The AI service is temporarily unavailable. Please try again shortly.",
  model_identity_mismatch: "The AI service is temporarily unavailable. Please try again later.",
  upstream_timeout: "Loading the paper took too long. Please try again.",
  paper_unavailable: "Couldn't load this paper's text from arXiv. Please try again shortly.",
  not_in_corpus: "This paper isn't in the search index, so it can't be discussed here.",
  outcome_unknown: "The request didn't complete. Please try again.",
  internal: "Something went wrong. Please try again.",
};

export function paperErrorText(error) {
  if (["rate_limited", "model_invalid_answer"].includes(error?.code) && error.message) return error.message;
  return PAPER_ERRORS[error?.code] || PAPER_ERRORS.outcome_unknown;
}

function validAnswer(data) {
  return typeof data?.answer === "string" && data.answer.trim() &&
    typeof data.grounded === "boolean" && Array.isArray(data.citations);
}

export class PaperConversation {
  constructor(paper, { transport }) {
    this.paper = paper;
    this.transport = transport;
    this.real = true;
    this.source = null;
    this.contextState = "idle";
    this.contextError = "";
    this.messages = [];
    this.busy = false;
    this.pendingQuestion = null;
    this.failedQuestion = null;
    this.error = "";
    this.draft = "";
  }

  get questionsLeft() {
    return PAPER_QUESTION_LIMIT - this.messages.length;
  }

  get canAsk() {
    return !this.busy && this.questionsLeft > 0;
  }

  async loadContext() {
    if (["loading", "ready"].includes(this.contextState)) return;
    this.contextState = "loading";
    this.contextError = "";
    try {
      const data = await this.transport("context", { arxiv_id: this.paper.arxiv_id });
      if (data?.paper?.arxiv_id !== this.paper.arxiv_id || !data.paper.coverage) throw new Error("Invalid paper context.");
      this.source = data.paper;
      this.contextState = "ready";
    } catch (error) {
      if (this.contextState === "ready") return;
      this.contextState = "error";
      this.contextError = paperErrorText(error);
    }
  }

  async ask(question) {
    const text = question.trim();
    if (!this.canAsk || !text || text.length > 500) return;
    this.busy = true;
    this.pendingQuestion = text;
    this.error = "";
    try {
      const data = await this.transport("ask", {
        arxiv_id: this.paper.arxiv_id, question: text,
        history: this.messages.map(m => ({ user: m.question, assistant: m.answer })),
      });
      if (!validAnswer(data)) throw new Error("Invalid paper answer.");
      if (data.paper?.arxiv_id === this.paper.arxiv_id && data.paper.coverage) {
        this.source = data.paper;
        this.contextState = "ready";
      }
      this.messages.push({ question: text, answer: data.answer, grounded: data.grounded, citations: data.citations });
      this.failedQuestion = null;
    } catch (error) {
      this.error = paperErrorText(error);
      this.failedQuestion = text;
    } finally {
      this.busy = false;
      this.pendingQuestion = null;
    }
  }

  retry() {
    return this.failedQuestion ? this.ask(this.failedQuestion) : Promise.resolve();
  }

  clear() {
    if (this.busy) return;
    this.messages = [];
    this.error = "";
    this.failedQuestion = null;
    this.draft = "";
  }
}
