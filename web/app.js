import { getMeta, isMock, search, summarize } from "./api.js";
import { CONFIG } from "./config.js";
import { openPaper, closePaper, previewPaperChat } from "./paper-chat.js";
import { notifyPortfolioReady } from "./portfolio.js";

const $ = (sel) => document.querySelector(sel);
const form = $("#search-form");
const input = $("#q");
const view = $("#results-view");
const resultsEl = $("#results");
const moreWrap = $("#more");
const moreBtn = $("#more-btn");
const moreSection = $("#more-section");
const moreResultsEl = $("#more-results");
const stateEl = $("#state");
const summaryEl = $("#summary");
const summaryBody = $("#summary-body");
const summaryMeta = $("#summary-meta");
const resultsMeta = $("#results-meta");

// Two-pane layout: results on the left, answer or paper on the right. ?layout=classic keeps the single column.
const SPLIT = new URLSearchParams(location.search).get("layout") !== "classic";
if (SPLIT) {
  document.body.classList.add("layout-split");
  const split = document.createElement("div");
  split.className = "split";
  const left = document.createElement("div");
  left.className = "split-left";
  const right = document.createElement("div");
  right.className = "split-right";
  left.append(...["#workspace-bar", "#search-form", "#composer-help", "#examples", "#notice", "#sr-status", "#results-view"]
    .map((sel) => $(sel)));
  right.append(summaryEl, $("#paper-workspace"));
  split.append(left, right);
  $("#main").append(split);

  const paperSplit = $(".paper-split");
  const leftKey = () => (document.body.classList.contains("paper-open") ? "leftPaper" : "left");
  split.insertBefore(addResizer({
    host: split,
    label: "Resize results pane",
    prop: () => `--${leftKey() === "left" ? "left-w" : "left-w-paper"}`,
    key: () => `arxiv.split.${leftKey()}`,
    pane: () => left,
    width: (x) => x - left.getBoundingClientRect().left,
    bounds: () => (leftKey() === "left" ? [300, split.clientWidth - 440] : [220, split.clientWidth - 740]),
    restore: [["--left-w", "arxiv.split.left"], ["--left-w-paper", "arxiv.split.leftPaper"]],
  }), right);
  paperSplit.insertBefore(addResizer({
    host: paperSplit,
    label: "Resize paper chat pane",
    className: "paper-resizer",
    direction: -1,
    prop: () => "--chat-w",
    key: () => "arxiv.split.chat",
    pane: () => $("#paper-discussion"),
    width: (x) => paperSplit.getBoundingClientRect().right - x,
    bounds: () => [280, paperSplit.clientWidth - 360],
    restore: [["--chat-w", "arxiv.split.chat"]],
  }), $("#paper-discussion"));
}

// Draggable, keyboard-accessible divider. Widths persist per pane in localStorage;
// CSS clamps them again so a window resize can't push a pane off screen.
function addResizer({ host, label, prop, key, pane, width, bounds, restore, className = "split-resizer", direction = 1 }) {
  const bar = document.createElement("div");
  bar.className = `resizer ${className}`;
  bar.tabIndex = 0;
  bar.setAttribute("role", "separator");
  bar.setAttribute("aria-orientation", "vertical");
  bar.setAttribute("aria-label", label);
  bar.title = "Drag to resize · double-click to reset";
  const store = (value) => { try { value == null ? localStorage.removeItem(key()) : localStorage.setItem(key(), value); } catch {} };
  const saved = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  for (const [name, k] of restore) {
    const v = Number(saved(k));
    if (v > 0) host.style.setProperty(name, `${v}px`);
  }
  const apply = (px) => {
    const [min, max] = bounds();
    const value = Math.round(Math.min(Math.max(px, min), Math.max(min, max)));
    host.style.setProperty(prop(), `${value}px`);
    bar.setAttribute("aria-valuemin", min);
    bar.setAttribute("aria-valuemax", Math.max(min, Math.round(max)));
    bar.setAttribute("aria-valuenow", value);
    return value;
  };
  const sync = () => {
    const [min, max] = bounds();
    bar.setAttribute("aria-valuemin", min);
    bar.setAttribute("aria-valuemax", Math.max(min, Math.round(max)));
    bar.setAttribute("aria-valuenow", Math.round(pane().getBoundingClientRect().width));
  };
  bar.addEventListener("focus", sync);
  bar.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    bar.setPointerCapture(event.pointerId);
    document.body.classList.add("resizing");
    let last = null;
    const move = (e) => { last = apply(width(e.clientX)); };
    const up = () => {
      bar.removeEventListener("pointermove", move);
      document.body.classList.remove("resizing");
      if (last != null) store(last);
    };
    bar.addEventListener("pointermove", move);
    bar.addEventListener("pointerup", up, { once: true });
    bar.addEventListener("pointercancel", up, { once: true });
  });
  bar.addEventListener("dblclick", () => {
    host.style.removeProperty(prop());
    store(null);
  });
  bar.addEventListener("keydown", (event) => {
    const step = event.shiftKey ? 64 : 16;
    const current = pane().getBoundingClientRect().width;
    const [min, max] = bounds();
    const next = {
      ArrowLeft: current - step * direction,
      ArrowRight: current + step * direction,
      Home: min,
      End: max,
    }[event.key];
    if (next == null) return;
    event.preventDefault();
    store(apply(next));
  });
  return bar;
}
const fallbackNote = $("#fallback-note");
const template = $("#result-template");
const wakeEl = $("#wake");
const srStatus = $("#sr-status");
const about = $("#about");

if (CONFIG.SHOWCASE_ONLY) {
  $(".intro > p:last-child").textContent = "Explore the design with sample papers. AI answers and paper chat are switched off.";
  $(".site-footer p").textContent = "Public design demo · No AI calls. PDFs load directly from arXiv.";
  $(".summary-foot").textContent = "Illustrative placeholder, not an AI-generated answer. Open the papers to read their findings.";
  $("#about .steps").insertAdjacentHTML("beforebegin",
    "<p class=\"showcase-note\">This public site demonstrates the design using sample data. The pipeline below describes the separate research system, not the demo running here.</p>");
}

let controller;
let lastQuery = "";
let searchPending = false;

// Announce once per change; the results themselves aren't a live region.
function announce(text) {
  srStatus.textContent = "";
  setTimeout(() => (srStatus.textContent = text), 50);
}

// ---------------------------------------------------------------- helpers

const escapeHtml = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const STOP = new Set(["the", "and", "for", "with", "from", "that", "this", "are", "how", "what", "into", "using", "based"]);

function termRegex(query) {
  const terms = [...new Set(query.toLowerCase().match(/[a-z0-9]+/g) ?? [])].filter((t) => t.length > 2 && !STOP.has(t));
  if (!terms.length) return null;
  return new RegExp(`\\b(${terms.join("|")})\\w*`, "gi");
}

// Splits raw text so only matched spans get wrapped; everything is escaped.
function highlight(text, re) {
  if (!re) return escapeHtml(text);
  let out = "";
  let last = 0;
  for (const m of text.matchAll(re)) {
    out += escapeHtml(text.slice(last, m.index)) + `<mark>${escapeHtml(m[0])}</mark>`;
    last = m.index + m[0].length;
  }
  return out + escapeHtml(text.slice(last));
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function formatMonth(ym) {
  const [y, m] = String(ym).split("-");
  return MONTHS[Number(m) - 1] ? `${MONTHS[Number(m) - 1]} ${y}` : ym;
}

function formatAuthors(authors = [], truncated = false) {
  if (authors.length > 3) return `${authors.slice(0, 3).join(", ")} et al.`;
  return authors.join(", ") + (truncated ? " et al." : "");
}

const seconds = (ms) => (ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.max(1, Math.round(ms))} ms`);

const skeleton = (lines = 3) => `<div class="skeleton">${"<span></span>".repeat(lines)}</div>`;
const spinner = (label) => `<span class="spinner" aria-hidden="true"></span>${escapeHtml(label)}`;

// User-facing text for API error codes; `where` is "search" or "summary".
function errorText(err, where) {
  const wait = err.retryAfter ? ` in ${err.retryAfter} seconds` : " in a moment";
  switch (err.code) {
    case "rate_limited":
      if (err.retryAfter > 120) {
        return { title: "Daily search limit reached", message: err.message || "Please come back tomorrow.", retry: false };
      }
      return { title: "Too many searches", message: `Please wait and try again${wait}.`, retry: true };
    case "budget_exhausted":
      return where === "summary"
        ? { message: "Today's AI answer budget is used up (resets at midnight UTC). The papers below are still ranked." }
        : { title: "Search limit reached", message: err.message || "The search budget has been used. More searches need to be enabled by the operator.", retry: false };
    case "upstream_unavailable":
      return { title: "Service temporarily unavailable", message: "A service we depend on isn't responding. Please try again shortly.", retry: true };
    case "bad_request":
      return { title: "Couldn't run that search", message: err.message, retry: false };
    case "not_deployed":
      return { title: "Search is coming soon", message: "The site is up, but the search service isn't live yet. Please check back soon.", retry: false };
    case "network":
      return { title: "Search failed", message: err.message, retry: true };
    case "timeout":
      return { title: "Search timed out", message: err.message, retry: true };
    default:
      return { title: "Something went wrong", message: "The search service hit an error. Please try again.", retry: true };
  }
}

// ------------------------------------------------------------------ meta

async function loadMeta() {
  try {
    const meta = await getMeta();
    const cats = (meta.categories ?? []).join(", ");
    $("#collection-label").textContent =
      `${Number(meta.papers).toLocaleString()} papers · ${formatMonth(meta.from_month)} – ${formatMonth(meta.to_month)}`;
    $("#notice-short").textContent =
      `Searches ${Number(meta.papers).toLocaleString()} arXiv papers (${cats}) from ` +
      `${formatMonth(meta.from_month)} to ${formatMonth(meta.to_month)}, using titles and abstracts. Not every paper is included.`;
    if (CONFIG.SHOWCASE_ONLY) {
      $("#collection-label").textContent = `${Number(meta.papers).toLocaleString()} sample papers · Design demo`;
      $("#notice-short").textContent = "This demo uses simple keyword matching on a static sample, not the full RAG index. Summaries and paper discussion are illustrative. No query is sent to a model.";
    }
    const extra = [meta.corpus_note];
    if (meta.baseline) extra.push(`Ranking system: ${meta.baseline.retrieval} → ${meta.baseline.reranking}.`);
    const text = extra.filter(Boolean).join(" ");
    if (text) {
      $("#notice-extra").textContent = text;
      $("#notice-extra").hidden = false;
    }
  } catch (err) {
    // Keep the static notice text; searches will surface their own errors.
    if (err.code === "not_deployed") $("#soon-badge").hidden = false;
  }
  $("#demo-badge").hidden = !isMock();
}

// --------------------------------------------------------------- render

function setState(kind, title, message, retry) {
  stateEl.hidden = false;
  stateEl.className = `state ${kind}`;
  stateEl.innerHTML = `<h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p>` +
    (retry ? `<button type="button" class="retry">Try again</button>` : "");
  stateEl.querySelector(".retry")?.addEventListener("click", () => runSearch(lastQuery, false));
}

function clearResults() {
  summaryEl.hidden = true;
  summaryEl.classList.remove("summary-unavailable");
  resultsEl.innerHTML = "";
  moreResultsEl.innerHTML = "";
  moreWrap.hidden = true;
  fallbackNote.hidden = true;
  resultsMeta.textContent = "";
  resultsMeta.removeAttribute("title");
  $(".summary-foot").hidden = false;
}

function showLoading() {
  clearResults();
  stateEl.hidden = true;
  summaryEl.hidden = false;
  summaryEl.setAttribute("aria-busy", "true");
  summaryBody.innerHTML = skeleton(3);
  summaryMeta.textContent = "";
  resultsMeta.innerHTML = spinner("Searching and reranking…");
  resultsEl.innerHTML = Array.from({ length: 4 }, () => `<li class="card result-skeleton">${skeleton(3)}</li>`).join("");
}

function buildResult(r, re) {
  const node = template.content.firstElementChild.cloneNode(true);
  node.id = `result-${r.rank}`;
  node.querySelector(".result-rank").textContent = r.rank;
  const link = node.querySelector(".result-title a");
  link.href = r.url || `https://arxiv.org/abs/${r.arxiv_id}`;
  link.innerHTML = highlight(r.title, re);
  // With a paper open in the split layout, the compact list switches papers.
  link.addEventListener("click", (event) => {
    if (!SPLIT || !document.body.classList.contains("paper-open")) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    openPaper(r, node.querySelector(".paper-chat-open"));
  });
  node.querySelector(".result-byline").textContent =
    [formatAuthors(r.authors, r.authors_truncated), formatMonth(r.submitted_month), `arXiv:${r.arxiv_id}`]
      .filter(Boolean).join(" · ");
  node.querySelector(".result-abstract").innerHTML = highlight(r.abstract ?? "", re);
  node.querySelector(".pdf-link").href = `https://arxiv.org/pdf/${r.arxiv_id}`;
  node.querySelector(".paper-chat-open").addEventListener("click", (event) => {
    openPaper(r, event.currentTarget);
  });

  const tags = node.querySelector(".result-tags");
  const cats = [r.primary_category, ...(r.categories ?? []).filter((c) => c !== r.primary_category)].slice(0, 4);
  tags.innerHTML = cats.map((c, i) => `<span class="tag${i === 0 ? " tag-primary" : ""}">${escapeHtml(c)}</span>`).join("");

  const toggle = node.querySelector(".toggle-abstract");
  toggle.setAttribute("aria-expanded", "false");
  toggle.addEventListener("click", () => {
    const open = node.classList.toggle("expanded");
    toggle.textContent = open ? "Show less" : "Show more";
    toggle.setAttribute("aria-expanded", open);
  });
  return node;
}

// Hide "Show more" when the abstract already fits in the clamp.
function fitToggles(list) {
  requestAnimationFrame(() => {
    for (const node of list.children) {
      const abs = node.querySelector(".result-abstract");
      node.querySelector(".toggle-abstract").hidden = abs.scrollHeight <= abs.clientHeight + 1;
    }
  });
}

function renderResults(results, re) {
  const top = results.slice(0, CONFIG.RESULTS_K);
  const more = results.slice(CONFIG.RESULTS_K);
  resultsEl.replaceChildren(...top.map((r) => buildResult(r, re)));
  moreResultsEl.replaceChildren(...more.map((r) => buildResult(r, re)));
  fitToggles(resultsEl);
  moreWrap.hidden = more.length === 0;
  moreSection.hidden = true;
  moreBtn.hidden = false;
  moreBtn.setAttribute("aria-expanded", "false");
  moreBtn.textContent = `Show ${more.length} more result${more.length === 1 ? "" : "s"}`;
}

moreBtn.addEventListener("click", () => {
  moreSection.hidden = false;
  moreBtn.hidden = true;
  moreBtn.setAttribute("aria-expanded", "true");
  fitToggles(moreResultsEl);
  moreResultsEl.firstElementChild?.querySelector(".result-title a")?.focus({ preventScroll: false });
});

// Only numbers listed in `cited` and within the result range become chips.
function renderSummary(text, cited, count) {
  const allowed = new Set((cited ?? []).map(Number).filter((n) => n >= 1 && n <= count));
  const paragraphs = String(text).trim().split(/\n\s*\n/).filter(Boolean);
  summaryBody.innerHTML = paragraphs
    .map((p) => {
      const html = escapeHtml(p).replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g, (whole, list) => {
        const nums = list.split(",").map((n) => Number(n.trim()));
        if (!nums.every((n) => allowed.has(n))) return whole;
        return nums
          .map((n) => `<button type="button" class="cite" data-rank="${n}" aria-label="Go to result ${n}">${n}</button>`)
          .join("");
      });
      return `<p>${html}</p>`;
    })
    .join("");
}

function renderUngrounded(text, cited, count) {
  renderSummary(
    text?.trim() || "The papers below may still be related. Try rephrasing your search or opening a paper.",
    cited, count,
  );
  summaryBody.insertAdjacentHTML("afterbegin",
    `<p class="summary-empty">No answer found in these abstracts.</p>` +
    (summaryBody.querySelector(".cite")
      ? `<p>Closest results — these papers do not answer the question directly.</p>` : ""));
  for (const chip of summaryBody.querySelectorAll(".cite")) {
    chip.setAttribute("aria-label", `Go to closest result ${chip.dataset.rank}`);
  }
}

summaryBody.addEventListener("click", (e) => {
  const btn = e.target.closest(".cite");
  if (!btn) return;
  const target = document.getElementById(`result-${btn.dataset.rank}`);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  for (const highlighted of view.querySelectorAll(".result.flash")) {
    highlighted.classList.remove("flash");
  }
  target.classList.add("flash");
  target.querySelector(".result-title a")?.focus({ preventScroll: true });
});

if (SPLIT) {
  for (const type of ["mouseover", "mouseout"]) {
    summaryBody.addEventListener(type, (e) => {
      const btn = e.target.closest(".cite");
      if (!btn) return;
      document.getElementById(`result-${btn.dataset.rank}`)?.classList.toggle("cite-hover", type === "mouseover");
    });
  }
}

// --------------------------------------------------------------- search

async function runSearch(rawQuery, push = true) {
  if (searchPending || !rawQuery.trim()) return;
  searchPending = true;
  const submit = form.querySelector('[type="submit"]');
  submit.disabled = true;
  try {
    await executeSearch(rawQuery, push);
  } finally {
    searchPending = false;
    submit.disabled = false;
  }
}

async function executeSearch(rawQuery, push) {
  const query = rawQuery.trim().replace(/\s+/g, " ");
  if (!query) return;
  lastQuery = query;
  if (SPLIT) closePaper();
  $("#composer-help").textContent = "";
  input.value = query;
  autosize();
  document.title = `${query} · arXiv Search`;
  if (push) history.pushState({ q: query }, "", `?${new URLSearchParams({ ...currentFlags(), q: query })}`);

  controller?.abort();
  controller = new AbortController();
  const { signal } = controller;

  document.body.classList.add("has-results");
  $("#workspace-bar").hidden = false;
  $("#question-title").textContent = query;
  view.hidden = false;
  $("#notice").open = false;
  showLoading();

  let data;
  // Show a wake-up message if the backend is cold-starting.
  const wakeTimer = setTimeout(() => {
    if (signal.aborted) return;
    wakeEl.hidden = false;
    announce("Still researching. Loading the collection and checking relevance can take a little time.");
  }, CONFIG.SLOW_START_MS);
  announce("Searching…");
  try {
    // In "auto" mode the meta probe decides live vs. demo data first.
    if (CONFIG.MODE === "auto") await metaReady;
    data = await search(query, signal);
  } catch (err) {
    if (err.name === "AbortError") return;
    clearResults();
    const e = errorText(err, "search");
    setState("error", e.title, e.message, e.retry);
    announce(`${e.title}. ${e.message}`);
    return;
  } finally {
    clearTimeout(wakeTimer);
    if (!signal.aborted) wakeEl.hidden = true;
  }
  if (signal.aborted) return;

  const results = data.results ?? [];
  if (!results.length) {
    clearResults();
    setState("empty", "No matching papers",
      "Try broader or different wording. The index only covers recent cs.IR, cs.CL and cs.LG papers, and not every paper is included.");
    announce("No matching papers.");
    return;
  }

  renderResults(results, termRegex(query));
  const shown = Math.min(results.length, CONFIG.RESULTS_K);
  const latency = data.meta?.latency_ms ? ` · ${seconds(data.meta.latency_ms)}` : "";
  resultsMeta.textContent = `${shown} results${latency}`;
  if (data.meta?.stage_detail) resultsMeta.title = data.meta.stage_detail;
  fallbackNote.hidden = !data.meta?.fallback;
  fallbackNote.textContent = data.meta?.stage === "lexical"
    ? "AI ranking is unavailable right now, so these are keyword matches."
    : "AI reranking is unavailable right now, so these results are in search order.";
  if (data.meta?.summary_available === false) {
    const unavailable = {
      authorization_unavailable: "The answer service is temporarily unavailable.",
      model_unavailable: "The AI service is temporarily unavailable.",
      daily_budget: "Today's AI budget is used up. AI answers and ranking return after midnight UTC.",
    }[data.meta?.summary_unavailable_reason] || "AI answers aren't enabled yet.";
    summaryBody.innerHTML = `<p>${escapeHtml(unavailable)} Showing relevant papers.</p>`;
    summaryEl.classList.add("summary-unavailable");
    $(".summary-foot").hidden = true;
    summaryEl.setAttribute("aria-busy", "false");
    announce(`${shown} papers found. ${unavailable}`);
    return;
  }
  announce(`${shown} papers found. Writing summary.`);

  // The summary covers only the top results the user sees first.
  const summarized = results.slice(0, CONFIG.RESULTS_K);
  summaryBody.innerHTML = `<p class="summary-loading">${spinner("Writing summary…")}</p>` + skeleton(3);
  try {
    const s = await summarize(query, summarized.map((r) => r.arxiv_id), signal, data.search_token);
    if (s.grounded === false) renderUngrounded(s.summary, s.cited, summarized.length);
    else if (!s.summary?.trim()) summaryEl.hidden = true;
    else renderSummary(s.summary, s.cited, summarized.length);
    summaryMeta.textContent = s.latency_ms ? seconds(s.latency_ms) : "";
    announce(s.grounded === false ? "No answer found in these abstracts." : "Summary ready.");
  } catch (err) {
    if (err.name === "AbortError") return;
    const msg = err.code === "budget_exhausted"
      ? errorText(err, "summary").message
      : "The summary isn't available right now. The papers below are still ranked by relevance.";
    summaryBody.innerHTML = `<p class="summary-error">${escapeHtml(msg)}</p>`;
  } finally {
    if (!signal.aborted) summaryEl.setAttribute("aria-busy", "false");
  }
}

// Keep debugging flags (?mock, ?api) when updating the URL.
function currentFlags() {
  const p = new URLSearchParams(location.search);
  const flags = {};
  for (const k of ["mock", "api", "clawpilotTheme", "layout"]) if (p.has(k)) flags[k] = p.get(k);
  return flags;
}

function resetHome() {
  closePaper();
  controller?.abort();
  wakeEl.hidden = true;
  document.body.classList.remove("has-results");
  $("#workspace-bar").hidden = true;
  view.hidden = true;
  input.value = "";
  autosize();
  $("#composer-help").textContent = "";
  document.title = "arXiv Search · Agarwal Labs";
}

function syncFromUrl() {
  const q = new URLSearchParams(location.search).get("q");
  resetHome();
  if (q) {
    input.value = q;
  autosize();
    $("#composer-help").textContent = "Question restored. Submit to search; loading this page does not spend a search.";
  }
}

// --------------------------------------------------------------- events

form.addEventListener("submit", (e) => {
  e.preventDefault();
  input.blur();
  runSearch(input.value);
});

function autosize() {
  if (!input.style) return;
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
}
input.addEventListener("input", autosize);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    form.requestSubmit();
  }
});

$("#examples").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) runSearch(chip.textContent);
});

function newQuestion(e) {
  e.preventDefault();
  const qs = new URLSearchParams(currentFlags()).toString();
  history.pushState({}, "", qs ? `?${qs}` : location.pathname);
  resetHome();
  input.focus();
}
document.querySelector("[data-home]").addEventListener("click", newQuestion);
$("#new-question").addEventListener("click", newQuestion);

document.addEventListener("keydown", (e) => {
  if (!$("#paper-workspace").hidden) return;
  if (e.key === "/" && !about.open && document.activeElement !== input && !e.target.closest("input, textarea")) {
    e.preventDefault();
    input.focus();
    input.select();
  } else if (e.key === "Escape" && document.activeElement === input) {
    input.blur();
  }
});

window.addEventListener("popstate", syncFromUrl);

$("#about-open").addEventListener("click", () => about.showModal());
$("#about-close").addEventListener("click", () => about.close());
// Clicks on the backdrop land on the <dialog> itself, not its inner wrapper.
about.addEventListener("click", (e) => {
  if (e.target === about) about.close();
});

// Metadata warms the backend without spending a search.
const metaReady = loadMeta();
syncFromUrl();
if (!document.body.classList.contains("has-results")) input.focus();
if (new URLSearchParams(location.search).get("paperDemo") === "1") previewPaperChat();
notifyPortfolioReady();
