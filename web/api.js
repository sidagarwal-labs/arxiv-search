import { CONFIG } from "./config.js";

const params = new URLSearchParams(location.search);
const apiBase = (params.get("api") ?? CONFIG.API_BASE).replace(/\/$/, "");
const scenario = params.get("mock") || "";
let MOCK = CONFIG.SHOWCASE_ONLY || params.has("mock") || CONFIG.MODE === "mock";
export const isMock = () => MOCK;

export class ApiError extends Error {
  constructor(message, code, retryAfter) {
    super(message);
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

async function request(path, body, signal) {
  // Generous timeout: a cold backend can take up to a minute to wake.
  const timeout = AbortSignal.timeout(CONFIG.REQUEST_TIMEOUT_MS);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
  let res;
  try {
    res = await fetch(apiBase + path, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: combined,
    });
  } catch (err) {
    if (signal?.aborted) throw err;
    if (timeout.aborted) throw new ApiError("The search service took too long to respond. Please try again.", "timeout");
    throw new ApiError("Can't reach the search service. Check your connection and try again.", "network");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok || data === null) {
    // A bare 404/405/501 (no JSON error body) means nothing is serving /api/* yet;
    // static hosts answer POSTs to missing paths with any of these.
    if ([404, 405, 501].includes(res.status) && !data?.error) {
      throw new ApiError("The search service hasn't been deployed yet.", "not_deployed");
    }
    const retryAfter = Number(res.headers.get("Retry-After")) || undefined;
    const code = data?.error?.code || (res.status === 429 ? "rate_limited" : res.status >= 500 ? "internal" : "unknown");
    throw new ApiError(data?.error?.message || `The service returned an unexpected response (${res.status}).`, code, retryAfter);
  }
  return data;
}

// ---------------------------------------------------------------- mock ----
// Mimics the real contract on a local sample so the UI can be built and
// reviewed before the API exists. Ranking here is naive term overlap.

let mockData;
async function loadMock() {
  if (!mockData) {
    try {
      const res = await fetch("./mock/papers.json");
      if (!res.ok) throw new Error();
      mockData = await res.json();
    } catch {
      throw new ApiError("Mock data is missing. Run web/scripts/make_mock_data.py first.", "mock");
    }
  }
  return mockData;
}

const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(t);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });

const tokenize = (s) => s.toLowerCase().match(/[a-z0-9]+/g) ?? [];

function mockError(code) {
  if (code === "rate_limited") return new ApiError("Too many requests.", code, 30);
  if (code === "budget_exhausted") return new ApiError("Daily budget exhausted.", code);
  return new ApiError("Upstream model unavailable.", "upstream_unavailable");
}

async function mockSearch(query, k, signal) {
  const started = performance.now();
  const { papers } = await loadMock();
  await sleep(scenario === "cold" ? 9000 : 700 + Math.random() * 900, signal);
  if (scenario === "rate_limited" || scenario === "budget_exhausted") throw mockError(scenario);
  const terms = [...new Set(tokenize(query))].filter((t) => t.length > 2);
  const scored = papers
    .map((p) => {
      const title = new Set(tokenize(p.title));
      const body = new Set(tokenize(p.abstract));
      const score = terms.reduce((s, t) => s + (title.has(t) ? 3 : 0) + (body.has(t) ? 1 : 0), 0);
      return { p, score };
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
  const fallback = scenario === "fallback";
  return {
    query,
    results: scored.map(({ p }, i) => ({
      rank: i + 1,
      ...p,
      authors: p.authors.slice(0, 10),
      authors_truncated: p.authors.length > 10,
    })),
    meta: {
      stage: fallback ? "retrieval" : "mock",
      stage_detail: "mock: term overlap on a 1,500-paper sample",
      fallback,
      latency_ms: Math.round(performance.now() - started),
    },
  };
}

async function mockSummary(query, ids, signal) {
  await sleep(1400 + Math.random() * 1000, signal);
  if (scenario === "summary_error") throw mockError("upstream_unavailable");
  if (scenario === "ungrounded" || !ids.length) {
    return { summary: "", cited: [], grounded: false, model: "mock", latency_ms: 0 };
  }
  const n = Math.min(3, ids.length);
  const cites = Array.from({ length: n }, (_, i) => `[${i + 1}]`).join(", ");
  const summary =
    `This is placeholder text from mock mode; the real summary will be written by an LLM from the top results. ` +
    `For "${query}", see papers ${cites}.\n\n` +
    `Markers outside the result list, like [${ids.length + 5}], stay plain text.`;
  return { summary, cited: Array.from({ length: n }, (_, i) => i + 1), grounded: true, model: "mock", latency_ms: 0 };
}

async function mockMeta() {
  const data = await loadMock().catch(() => ({ meta: {} }));
  return {
    ...CONFIG.FALLBACK_META,
    ...data.meta,
    ...(CONFIG.SHOWCASE_ONLY ? { papers: data.papers?.length ?? 0 } : {}),
    corpus_note: "Demo mode: searching a 1,500-paper sample, not the full index.",
    baseline: { retrieval: "mock", reranking: "none" },
  };
}

// --------------------------------------------------------------- public ----

// Call once at startup; in "auto" mode this decides between live and mock.
export async function getMeta() {
  if (MOCK) return mockMeta();
  try {
    return await request("/api/meta");
  } catch (err) {
    if (CONFIG.MODE !== "auto" || params.has("api")) throw err;
    MOCK = true;
    return mockMeta();
  }
}

export async function search(query, signal) {
  if (MOCK) return mockSearch(query, CONFIG.FETCH_K, signal);
  return request("/api/search", { query, k: CONFIG.FETCH_K }, signal);
}

export async function summarize(query, arxivIds, signal, searchToken) {
  if (MOCK) return mockSummary(query, arxivIds, signal);
  return request("/api/summary", {
    query, arxiv_ids: arxivIds, ...(searchToken ? { search_token: searchToken } : {}),
  }, signal);
}
