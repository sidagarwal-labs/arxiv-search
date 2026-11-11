// Deployment settings.
// MODE: "live" calls the API; "mock" uses local sample data; "auto" tries the
// API and falls back to mock (with a visible "Demo data" badge) if it's absent.
// In live mode, missing /api/* routes are a deployment error, not demo mode.
// Per-visit overrides: ?api=https://host,
// ?mock=1, or a mock scenario: ?mock=fallback|ungrounded|rate_limited|budget_exhausted|summary_error|cold
export const CONFIG = {
  // Enabled only in the public static showcase package. Never enables API calls.
  SHOWCASE_ONLY: false,
  // Local dev tries the API and falls back to demo data; deployed sites are always live.
  MODE: ["localhost", "127.0.0.1"].includes(location.hostname) ? "auto" : "live",
  // Empty = same origin (Vercel serves /api/* next to the site, no CORS needed).
  API_BASE: "",
  // Offline implementation only. Deliberate activation is required; URL overrides
  // and search mock/live mode never enable paper requests.
  PAPER_API_ENABLED: true,
  PAPER_PREPARE_ONLY: false,
  PAPER_API_BASE: "",
  // Quality is measured at 10; ranks 11-20 are shown behind "More results".
  RESULTS_K: 10,
  FETCH_K: 20,
  // After this long without results, show the "waking up the server" message.
  SLOW_START_MS: 5000,
  REQUEST_TIMEOUT_MS: 150000,
  // Shown in the limitations notice until /api/meta answers.
  FALLBACK_META: {
    papers: 23304,
    categories: ["cs.CL", "cs.IR", "cs.LG"],
    from_month: "2025-10",
    to_month: "2026-10",
    fields: "title+abstract",
  },
};
