import { CONFIG } from "./config.js";
import { PaperConversation, createPaperTransport, citationURL } from "./paper-api.js";
import { renderReader, setPaperView } from "./paper-reader.js";

const $ = (selector) => document.querySelector(selector);
const workspace = $("#paper-workspace");
const transcript = $("#paper-transcript");
const conversations = new Map();
const question = $("#paper-question");
let active;
let returnFocus;
let returnScroll = 0;

function richMessage(role, nodes) {
  const article = document.createElement("article");
  article.className = `paper-message paper-message-${role}`;
  const label = document.createElement("h2");
  label.textContent = role === "user" ? "You" : "Paper assistant";
  article.append(label, ...nodes);
  return article;
}

function message(role, text) {
  const article = document.createElement("article");
  article.className = `paper-message paper-message-${role}`;
  const label = document.createElement("h2");
  label.textContent = role === "user" ? "You" : "Paper assistant";
  const body = document.createElement("p");
  body.textContent = text;
  article.append(label, body);
  return article;
}

function render() {
  renderReader(active);
  if (active.real) return renderReal();
  $("#paper-mode").textContent = "Preview";
  $("#paper-note").hidden = true;
  $("#paper-disclosure").hidden = true;
  $("#paper-actions").replaceChildren();
  transcript.removeAttribute("aria-busy");
  $("#paper-suggestions").replaceChildren(...DEMO_SHORTCUTS.map(text => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = text;
    chip.disabled = true;
    return chip;
  }));
  const intro = message("assistant",
    "Ask about this paper's method, data, results or limitations. Answers will cite the sections they come from.");
  intro.append(paragraphNode("AI coverage: not connected in this preview. Read the PDF on the left.", "paper-evidence-label"));
  transcript.replaceChildren(intro);
  $("#paper-suggestions").hidden = false;
  question.disabled = true;
  $("#paper-form button").disabled = true;
  $("#paper-clear").hidden = true;
  $("#paper-help").textContent = "AI discussion coming soon";
  $("#paper-status").textContent = "";
}

const DEMO_SHORTCUTS = [
  "Summarize this paper", "Method", "Datasets & benchmarks", "Results", "Limitations",
];

function paragraphNode(text, className) {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = text;
  return p;
}

const LIVE_SUGGESTIONS = [
  "Summarize this paper", "What method do they use?", "What data and benchmarks?",
  "What are the main results?", "What are the limitations?",
];
const MARKER = /\[([A-Za-z][A-Za-z0-9_.:-]{0,127})\]/g;

function shortLabel(citation) {
  const label = (citation.label || citation.id).replace(/[.:;,\s]+$/, "");
  const section = label.match(/^(\d+(?:\.\d+)*|[A-Z](?:\.\d+)*)\s/);
  if (section) return `§${section[1]}`;
  return label.length > 28 ? `${label.slice(0, 27)}…` : label;
}

function citeChip(citation, paper) {
  const href = citationURL(citation.href, paper);
  const node = document.createElement(href ? "a" : "span");
  node.className = "cite paper-cite";
  node.textContent = shortLabel(citation);
  node.title = citation.label || citation.id;
  if (href) {
    node.href = href;
    node.target = "_blank";
    node.rel = "noopener noreferrer";
  }
  return node;
}

// Plain text with [locator] markers turned into source chips; unknown markers stay text.
function answerNodes(text, citations, paper) {
  const byId = new Map((citations ?? []).map(c => [c.id, c]));
  return text.split(/\n{2,}/).filter(part => part.trim()).map(part => {
    const p = document.createElement("p");
    let last = 0;
    for (const match of part.matchAll(MARKER)) {
      const citation = byId.get(match[1]);
      if (!citation) continue;
      p.append(part.slice(last, match.index), citeChip(citation, paper));
      last = match.index + match[0].length;
    }
    p.append(part.slice(last));
    return p;
  });
}

function coverageSummary(c) {
  if (c.contextState === "loading") return "Reading the paper from arXiv…";
  if (c.contextState === "error") return c.contextError;
  const s = c.source;
  if (!s) return "";
  const version = s.version ? ` (v${s.version})` : "";
  if (s.source === "html") {
    return `Answers use the paper's full text${version}` +
      (s.coverage.truncated ? ", with some long sections left out" : "") + ".";
  }
  if (s.source === "pdf") return `Answers use text extracted from the PDF${version}. Figures and some equations may be missing.`;
  return "Only the abstract is available for this paper, so answers are limited to it.";
}

function renderCoverage(c) {
  const disclosure = $("#paper-disclosure");
  disclosure.replaceChildren();
  const text = coverageSummary(c);
  disclosure.hidden = !text;
  disclosure.classList.toggle("coverage-limited", c.source?.source === "abstract" || c.contextState === "error");
  const summary = document.createElement("summary");
  summary.textContent = text;
  disclosure.append(summary);
  if (!c.source?.coverage) return;
  const coverage = c.source.coverage;
  const included = (coverage.included_sections ?? []).map(x => x.label || x.id).join(", ");
  const omitted = (coverage.omitted ?? []).map(x => x.label || x.id).join(", ");
  disclosure.append(paragraphNode(`Included: ${included || "none"}.`));
  if (omitted) disclosure.append(paragraphNode(`Left out: ${omitted}.`));
  disclosure.append(paragraphNode(coverage.figures === "captions_only"
    ? "Figures: captions only (the AI can't see images)." : "Figures: not available to the AI."));
}

function renderReal() {
  const c = active;
  $("#paper-mode").textContent = "AI";
  $("#paper-note").hidden = true;
  $("#paper-coverage").textContent = "";
  renderCoverage(c);
  transcript.replaceChildren();
  if (!c.messages.length && !c.busy) {
    transcript.append(message("assistant",
      "Ask anything about this paper: its method, data, results or limitations. Answers cite the sections they come from."));
    transcript.lastChild?.classList?.add?.("paper-message-intro");
  }
  for (const turn of c.messages) {
    transcript.append(message("user", turn.question));
    const article = richMessage("assistant", answerNodes(turn.answer, turn.citations, c.source));
    if (!turn.grounded) {
      article.append(paragraphNode("Not clearly answered in the paper's text.", "paper-evidence-label"));
    }
    transcript.append(article);
  }
  if (c.busy) {
    transcript.append(message("user", c.pendingQuestion));
    const spinner = document.createElement("span");
    spinner.className = "spinner";
    spinner.setAttribute("aria-hidden", "true");
    const thinking = document.createElement("p");
    thinking.append(spinner, "Reading the paper…");
    transcript.append(richMessage("assistant", [thinking]));
  }
  transcript.setAttribute("aria-busy", String(c.busy));
  const actions = $("#paper-actions");
  actions.replaceChildren();
  if (c.error && c.failedQuestion && !c.busy) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "more-btn";
    retry.textContent = "Try again";
    retry.addEventListener("click", () => ask(() => c.retry()));
    actions.append(retry);
  }
  if (c.contextState === "error" && !c.busy) {
    const reload = document.createElement("button");
    reload.type = "button";
    reload.className = "more-btn";
    reload.textContent = "Retry loading paper";
    reload.addEventListener("click", () => loadContext(c));
    actions.append(reload);
  }
  $("#paper-status").textContent = c.error || (c.questionsLeft <= 0
    ? "You've reached the 10-question limit for this paper. Clear the conversation to start over." : "");
  question.disabled = c.questionsLeft <= 0;
  question.maxLength = 500;
  $("#paper-form button").disabled = !c.canAsk;
  $("#paper-clear").hidden = !c.messages.length;
  $("#paper-clear").disabled = c.busy;
  const suggestions = $("#paper-suggestions");
  suggestions.replaceChildren(...LIVE_SUGGESTIONS.map(text => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = text;
    chip.disabled = !c.canAsk;
    return chip;
  }));
  suggestions.hidden = c.messages.length > 0 || c.busy;
  $("#paper-help").textContent = `This paper only · ${Math.max(0, c.questionsLeft)} of 10 questions left · Sent to OpenAI and logged, so don't include private information`;
  transcript.scrollTop = transcript.scrollHeight;
}

function ask(work) {
  const conversation = active;
  const pending = work();
  render();
  return pending.then(() => {
    if (active === conversation && !workspace.hidden) render();
  });
}

function loadContext(conversation) {
  const pending = conversation.loadContext();
  if (active === conversation && !workspace.hidden) render();
  pending.then(() => {
    if (active === conversation && !workspace.hidden) render();
  });
}

export function openPaper(paper, trigger) {
  if (!workspace.hidden) closePaper();
  returnFocus = trigger;
  returnScroll = window.scrollY;
  if (!conversations.has(paper.arxiv_id)) {
    conversations.set(paper.arxiv_id, !CONFIG.SHOWCASE_ONLY && CONFIG.PAPER_API_ENABLED === true && paper.arxiv_id !== "interface-demo"
      ? new PaperConversation(paper, { transport: createPaperTransport({ base: CONFIG.PAPER_API_BASE }) })
      : { paper, draft: "" });
  }
  active = conversations.get(paper.arxiv_id);
  $("#paper-clear").hidden = false;
  $("#paper-title").textContent = paper.title;
  $("#paper-authors").textContent = (paper.authors ?? []).slice(0, 3).join(", ");
  $("#paper-source").href = `https://arxiv.org/abs/${encodeURIComponent(paper.arxiv_id)}`;
  $("#paper-source").hidden = paper.arxiv_id === "interface-demo";
  const split = document.body.classList.contains?.("layout-split");
  $("#paper-back").textContent = trigger ? (split ? "← Back to answer" : "← Back to results") : "← Back to search";
  trigger?.closest?.(".result")?.classList.add("active-paper");
  $("#paper-coverage").textContent = "";
  question.value = active.draft;
  autosize(question);
  document.body.classList.add("paper-open");
  workspace.hidden = false;
  render();
  $("#paper-reader-body").scrollTop = active.readerScroll ?? 0;
  window.scrollTo(0, 0);
  $("#paper-title").focus({ preventScroll: true });
  if (active.real) loadContext(active);
}

export function closePaper() {
  if (workspace.hidden) return;
  active.draft = question.value;
  active.readerScroll = $("#paper-reader-body").scrollTop;
  workspace.hidden = true;
  document.body.classList.remove("paper-open");
  returnFocus?.closest?.(".result")?.classList.remove("active-paper");
  if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
  window.scrollTo(0, returnScroll);
}

$("#paper-back").addEventListener("click", closePaper);
$("#paper-clear").addEventListener("click", () => {
  if (!active.real) return;
  active.clear();
  question.value = "";
  autosize(question);
  render();
});
$("#paper-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!active.real || !active.canAsk || !text || text.length > 500) return;
  question.value = "";
  autosize(question);
  ask(() => active.ask(text)).then(() => {
    if (active.failedQuestion === text && !question.value) {
      question.value = text;
      autosize(question);
    }
  });
});
export function autosize(field) {
  if (!field.style) return;
  field.style.height = "auto";
  field.style.height = `${Math.min(field.scrollHeight, 160)}px`;
}
question.addEventListener("input", () => autosize(question));
question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    $("#paper-form").requestSubmit();
  }
});
$("#paper-suggestions").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip || chip.disabled || !active.real || !active.canAsk) return;
  ask(() => active.ask(chip.textContent));
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !workspace.hidden && !$("#about").open) closePaper();
});

$("#paper-read-tab").addEventListener("click", () => setPaperView(active, "read"));
$("#paper-discuss-tab").addEventListener("click", () => setPaperView(active, "discuss"));
$("#paper-viewer-toggle").addEventListener("click", () => {
  active.viewerUnavailable = !active.viewerUnavailable;
  render();
});

export function previewPaperChat() {
  const selected = new URLSearchParams(location.search).get("preparePaper");
  if (CONFIG.PAPER_PREPARE_ONLY && /^\d{4}\.\d{4,5}$/.test(selected ?? "")) {
    openPaper({ arxiv_id: selected, title: "Inspect this corpus paper", authors: [] });
    return;
  }
  openPaper({
    arxiv_id: "interface-demo", title: "Explore a paper, one question at a time", authors: [],
  });
}
