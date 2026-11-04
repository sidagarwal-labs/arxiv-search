import { getMeta, isMock, search, summarize } from "./api.js";
import { CONFIG } from "./config.js";

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
const fallbackNote = $("#fallback-note");
const template = $("#result-template");
const wakeEl = $("#wake");
const srStatus = $("#sr-status");
const about = $("#about");

let controller;
let lastQuery = "";

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
      return { title: "Too many searches", message: `Please wait and try again${wait}.`, retry: true };
    case "budget_exhausted":
      return where === "summary"
        ? { message: "Summaries are paused for today because the daily limit was reached. The papers below are still ranked." }
        : { title: "Daily limit reached", message: "This demo has used today's search budget. Please come back tomorrow.", retry: false };
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
    $("#notice-short").textContent =
      `Searches ${Number(meta.papers).toLocaleString()} arXiv papers (${cats}) from ` +
      `${formatMonth(meta.from_month)} to ${formatMonth(meta.to_month)}, using titles and abstracts. Not every paper is included.`;
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
  resultsEl.innerHTML = "";
  moreResultsEl.innerHTML = "";
  moreWrap.hidden = true;
  fallbackNote.hidden = true;
  resultsMeta.textContent = "";
  resultsMeta.removeAttribute("title");
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
  node.querySelector(".result-byline").textContent =
    [formatAuthors(r.authors, r.authors_truncated), formatMonth(r.submitted_month), `arXiv:${r.arxiv_id}`]
      .filter(Boolean).join(" · ");
  node.querySelector(".result-abstract").innerHTML = highlight(r.abstract ?? "", re);
  node.querySelector(".pdf-link").href = `https://arxiv.org/pdf/${r.arxiv_id}`;

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

function renderUngrounded(text) {
  summaryBody.innerHTML =
    `<p class="summary-empty">No answer found in these abstracts.</p>` +
    `<p>${text?.trim() ? escapeHtml(text.trim()) : "The papers below may still be related. Try rephrasing your search or opening a paper."}</p>`;
}

summaryBody.addEventListener("click", (e) => {
  const btn = e.target.closest(".cite");
  if (!btn) return;
  const target = document.getElementById(`result-${btn.dataset.rank}`);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.remove("flash");
  void target.offsetWidth;
  target.classList.add("flash");
  target.querySelector(".result-title a")?.focus({ preventScroll: true });
});

// --------------------------------------------------------------- search

async function runSearch(rawQuery, push = true) {
  const query = rawQuery.trim().replace(/\s+/g, " ");
  if (!query) return;
  lastQuery = query;
  input.value = query;
  document.title = `${query} · arXiv Search`;
  if (push) history.pushState({ q: query }, "", `?${new URLSearchParams({ ...currentFlags(), q: query })}`);

  controller?.abort();
  controller = new AbortController();
  const { signal } = controller;

  document.body.classList.add("has-results");
  view.hidden = false;
  $("#notice").open = false;
  showLoading();

  let data;
  // Show a wake-up message if the backend is cold-starting.
  const wakeTimer = setTimeout(() => {
    if (signal.aborted) return;
    wakeEl.hidden = false;
    announce("Waking up the search server. This can take up to a minute.");
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
  announce(`${shown} papers found. Writing summary.`);

  // The summary covers only the top results the user sees first.
  const summarized = results.slice(0, CONFIG.RESULTS_K);
  summaryBody.innerHTML = `<p class="summary-loading">${spinner("Writing summary…")}</p>` + skeleton(3);
  try {
    const s = await summarize(query, summarized.map((r) => r.arxiv_id), signal);
    if (s.grounded === false) renderUngrounded(s.summary);
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
  for (const k of ["mock", "api"]) if (p.has(k)) flags[k] = p.get(k);
  return flags;
}

function resetHome() {
  controller?.abort();
  wakeEl.hidden = true;
  document.body.classList.remove("has-results");
  view.hidden = true;
  input.value = "";
  document.title = "arXiv Search · Agarwal Labs";
}

function syncFromUrl() {
  const q = new URLSearchParams(location.search).get("q");
  if (q) runSearch(q, false);
  else resetHome();
}

// --------------------------------------------------------------- events

form.addEventListener("submit", (e) => {
  e.preventDefault();
  input.blur();
  runSearch(input.value);
});

$("#examples").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) runSearch(chip.textContent);
});

document.querySelector("[data-home]").addEventListener("click", (e) => {
  e.preventDefault();
  const qs = new URLSearchParams(currentFlags()).toString();
  history.pushState({}, "", qs ? `?${qs}` : location.pathname);
  resetHome();
  input.focus();
});

document.addEventListener("keydown", (e) => {
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

// Not awaited: the meta request doubles as a warm-up ping for a cold backend,
// and shared ?q= links shouldn't wait on it to show the loading state.
const metaReady = loadMeta();
syncFromUrl();
if (!document.body.classList.contains("has-results")) input.focus();
