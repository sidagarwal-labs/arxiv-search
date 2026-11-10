# Web UI

A single search page: the user types a query, sees the top papers from retrieval,
then an AI summary of those papers with clickable `[n]` citations. A notice under
the search bar explains what the index does and doesn't cover.

Plain HTML/CSS/JS (ES modules), no build step and no dependencies.

**Current production:** the UI and Python API run together on Vercel at
`https://arxiv.agarwal-labs.com`, with D50 reranking, D49 summaries and live
stateless paper discussion enabled. The demo/offline and preview descriptions
below document older stages. Deploy the committed full application using the
[serving runbook](../serving/README.md#deploy-only-committed-source), not this
static directory alone.

## Paper workspace (demo by default; offline-wired API)

Each result has a **Discuss paper** action opening a dedicated, responsive
workspace. Back restores the existing results, focus and scroll without another
search.

With `CONFIG.PAPER_API_ENABLED: false` (the committed default), the Discuss pane
is labeled **Preview**: it shows the intended empty state (intro, five question
shortcuts, composer) with shortcuts and composer disabled and "AI discussion
coming soon". There are no demo buttons, placeholder answers or fake citations,
and nothing is sent anywhere. The search summary remains separate. The preview
navigation always opens this state, even if API mode is enabled.

The real frontend path is implemented but **not activated or deployed**. Only a
deliberate source configuration change to `PAPER_API_ENABLED: true` enables it;
search `MODE`, `?api=` and `?mock=` do not enable or redirect paper requests.
`PAPER_API_BASE` defaults to the same origin and is independent of search.
No live paper calls were used to implement or validate this path.

Opening/reopening a workspace does not call paper APIs. Clicking **Discuss paper**
automatically embeds the original PDF directly from arxiv.org in the browser,
without a second load button. This contacts arXiv, not the model service; it is
not AI extraction and does not change model coverage.
The user must click:

1. **Prepare paper — inspect source**: `POST /api/paper/prepare` with
   `{arxiv_id, request_id}`. Displays the returned source/version, included
   sections, omissions, truncation, warnings, figures/equation availability,
   outline and overview-cache state. PDF locators are physical pages; references
   may remain mixed into page text. No generated overview exists yet.
2. **Continue — open overview**: only after preparation returns
   `{preparation, paper: {coverage, outline, ...}, overview_cache,
   limits: {expires_at}, consent_required: true}`. Sends
   `{preparation, request_id}` to `/api/paper/open`. Keeps the returned `session`,
   signed overview (full `text`, `assistant_sig`, `turn_index: 0`), citations,
   `suggested_questions`, server `limits` and `cache`.
3. Explicit question submit sends `{session, request_id, messages, question}` to
   `/api/paper/chat`. `messages` contains the complete signed overview baseline
   and every complete user/assistant exchange, without locally truncating or
   summarizing history. Assistant history uses `{role, content, sig, turn_index}`;
   user history uses `{role, content}`. The response's `answer`, `grounded`,
   `citations`, `assistant_sig`, `turn_index`, `limits` and `memory` are retained.
   The server turn index and allowance are authoritative, including gaps caused
   by reserved/failed turns. The question cap is 500 characters.

No automatic retries occur. A failed operation retains its exact payload and
request ID; **Retry same request** is explicit, never a new operation. Unknown
outcomes may have used allowance. `session_busy` asks the user to wait and retry
that same request. `already_completed` (409) is nonrecoverable if the original
response was lost: it does not replay or create a fresh request. Chat `model_invalid_answer` is terminal for that question: its turn remains used, top-level error `limits` are applied, and only a new explicit question gets a new ID. Overview validation failure blocks reopening. Known server errors from prepare are terminal for that request ID (a same-ID retry would return `already_completed`), so no same-ID retry is offered. Unrecoverable paper errors (`bad_request` for an invalid ID, `not_in_corpus`) block preparation. Other known errors, including `paper_unavailable`, `upstream_timeout`, `already_completed` and an expired preparation, offer only **Prepare again (new request)**; failed allowance is not refunded. A network failure or malformed reply leaves prepare pending with only a same-ID retry, because it may have committed. Expiry and quota
exhaustion disable new questions but retain the transcript. Clear deletes local
history, draft and session credentials and makes that per-paper workspace
nonrenewable in this tab; it does not reset server quota. Reload discards browser
memory only, not server accounting. Nothing is written to browser storage.

Citation and outline links are created only for exact HTTPS `arxiv.org` source
paths bound to the returned paper ID, version and source, with HTML section
anchors or PDF physical-page locators. Invalid links remain plain labels.
Ungrounded replies label citations **Closest sections, not supporting evidence**.
Loading uses only a generic spinner, with no wait-time claims.

`paper-api.js` exports a DOM-free `PaperController` accepting injected transport,
clock and request-ID factory. `createPaperTransport` also accepts an injected
fetcher. Dependency-free offline tests (all fetches stubbed):

```powershell
node --experimental-default-type=module --test web\paper-api.test.mjs
```

Searches require an explicit submit or example click. Loading, refreshing or
returning to a `?q=` URL restores the question but does not call `/api/search`.
While search and its answer are pending, repeat form submissions, Enter and
example clicks are ignored and the submit button is disabled. Browser aborts
cannot refund already-reserved server calls.

This fixes a protected-trial spending hazard found November 4: request logs
showed searches at 19:38:57 UTC and 21:03:39 UTC, with the second immediately
following page/asset loading. The old immutable frontend reproduced one new
search on every load/reload of a query URL. The exact refresh/reopen gesture
is not recorded, but this was not a simultaneous Enter/form double submission.
Offline browser fixtures verified zero searches on load, reload and history
restoration; repeated submit/Enter/example events during a held request produced
exactly one search and one summary.

| File | Purpose |
|---|---|
| `index.html` | Page structure, limitations notice, result template |
| `styles.css` | Research workspace theme, responsive layout, loading skeletons |
| `theme.js` | Early light/dark theme selection without inline scripts |
| `app.js` | Search flow, URL state (`?q=`), rendering, citations, keyboard shortcuts |
| `api.js` | API client plus a mock that follows the same contract |
| `paper-chat.js` | Compact workspace, explicit demo and gated paper API UI |
| `paper-api.js` | Injectable paper transport/controller and strict citation validation |
| `paper-api.test.mjs` | Offline Node controller and frontend wiring tests |
| `config.js` | `MODE` (`auto`/`live`/`mock`), `API_BASE`, number of results |
| `vercel.json` | Static hosting settings and security headers, including a Content-Security-Policy |
| `favicon.svg`, `apple-touch-icon.png` | Browser and home-screen icons |
| `og-image.png` | 1200×630 link-preview image for social sites and chat apps |
| `robots.txt`, `sitemap.xml` | Crawler hints for the single public page |
| `scripts/make_mock_data.py` | Builds the git-ignored `mock/papers.json` sample from the local corpus |
| `scripts/og-image.html`, `scripts/apple-touch-icon.html` | Sources for the two PNGs (see below) |

## Run locally

```powershell
# From the arxiv-search folder
.\.venv\Scripts\python.exe web\scripts\make_mock_data.py   # once; needs data/processed/corpus.jsonl
.\.venv\Scripts\python.exe -m http.server 5173 --directory web
# open http://127.0.0.1:5173
```

On localhost the page runs in `auto` mode: it calls `/api/meta`, and if no API
answers, it uses the mock data and shows a **Demo data** badge. Per-visit overrides:

- `?api=http://127.0.0.1:8000` points at a local API.
- `?mock=1` forces mock mode.
- `?mock=<scenario>` previews one UI state: `fallback`, `ungrounded`,
  `rate_limited`, `budget_exhausted`, `summary_error` or `cold` (a 9 s first
  response that shows the wake-up message).

Mock ranking is simple term overlap on a 1,500-paper sample. It is only for
building the UI and says nothing about real search quality.

## API contract

Agreed with the backend chat on 2026-11-03. A separate protected
[serving preview](../serving/README.md) implements this contract with guarded
live embedding, reranking and (in release v2) cited-answer adapters. Production
remains a static site; protected trial usage is separately capped. The page
expects these endpoints on the same origin (or `API_BASE`). CORS should allow
`https://arxiv.agarwal-labs.com` and `http://localhost:*`.

`GET /api/meta` fills in the limitations notice. `corpus_note` and `baseline` are
shown at the bottom of the notice's details.

```json
{ "papers": 23304, "categories": ["cs.CL", "cs.IR", "cs.LG"],
  "from_month": "2025-10", "to_month": "2026-10", "fields": "title+abstract",
  "corpus_note": "...", "baseline": { "retrieval": "...", "reranking": "..." } }
```

`POST /api/search` with `{ "query": str, "k": 20 }` (default 10, max 20) returns
the ranked papers:

```json
{ "query": "...", "search_token": "opaque single-use token in the live answer release",
  "results": [{ "rank": 1, "arxiv_id": "2510.00027", "title": "...",
                "authors": ["first 10 only"], "authors_truncated": false,
                "abstract": "full text", "primary_category": "cs.LG", "categories": ["cs.LG"],
                "submitted_month": "2025-10", "url": "https://arxiv.org/abs/2510.00027" }],
  "meta": { "stage": "reranked", "stage_detail": "...", "fallback": false,
            "refined": true, "summary_available": true, "latency_ms": 2900 } }
```

- The page asks for 20 results in one request. It shows the top 10 and puts ranks
  11-20 behind "Show more results", labeled as unmeasured (quality is measured
  with nDCG@10).
- `stage: "retrieval"` with `fallback: true` means the reranker failed, timed out
  or ran out of budget. The page shows a subtle note, not an error.
- Optional `meta.refined` distinguishes Decision 47 refinement from Decision 46.
  Refinement failure preserves reranked papers, not retrieval fallback.
- `latency_ms` is shown for information only; the page shows a spinner and never
  promises a wait time. `stage_detail` appears as a tooltip on the result count.
- Optional `meta.summary_available: false` shows an explicit summary-unavailable
  notice and skips `/api/summary`. When absent or true, the existing summary flow
  is unchanged. Search budgets may be total-trial limits, not daily limits;
  exhaustion shows the server message and never promises a reset tomorrow.

`POST /api/summary` with `{ "query": str, "arxiv_ids": [str], "search_token": str }`
(the top 10, in rank order) returns the summary. The page forwards a token only
when search supplied one, preserving older APIs/mocks. In the live answer release
it is required, bound to this release/query/ordered evidence, and consumed once
before generation. Failed answers cannot retry with the same token; the page
does not automatically retry. If issuance is unavailable, papers remain visible
with a short answer-service notice instead of a misleading disabled-model notice.

```json
{ "summary": "Paragraphs separated by blank lines, citing papers as [1] or [1, 3].",
  "cited": [1, 3], "grounded": true, "model": "...", "latency_ms": 1800 }
```

- `[n]` markers are 1-based positions in `arxiv_ids`. A marker becomes a clickable
  chip only if every number in it is in `cited` and in range; anything else stays
  plain text.
- `grounded: false` means the model abstained. The page shows "No answer found in
  these abstracts" and keeps the results. Decision 49 (Luna / `answer-v2`,
  Contract B) may cite the closest papers even when they do not answer the query.
  Those markers remain clickable, explicitly framed as "Closest results", not
  supporting evidence. Grounded answers still require citations.
- Clicking a citation highlights only its target paper; previous citation
  highlights are cleared.
- The summary is a separate request so results appear first. If it fails, the
  results stay on screen with a short message.

Errors return a non-2xx status with `{ "error": { "code": str, "message": str } }`.
The page maps each code to its own wording:

| Code | Search | Summary |
|---|---|---|
| `rate_limited` (429 + `Retry-After`) | "Too many searches", with the wait time and a retry button | Generic "summary isn't available" |
| `budget_exhausted` | "Search limit reached", server explanation, no retry | "The summary limit was reached. The papers below are still ranked." |
| `upstream_unavailable` | "Service temporarily unavailable", retry | Generic message |
| `bad_request` | Shows the server's `message` | Generic message |
| `internal` / other | "Something went wrong", retry | Generic message |

For local cross-origin testing, the API needs `Access-Control-Expose-Headers: Retry-After`
or the browser hides the wait time; the page then says "in a moment". Same-origin
production doesn't need this.

### Cold starts

A free backend tier may take 30-60 s to answer the first request after it has been
idle. The page handles this in three ways:

- It requests `/api/meta` as soon as it loads, which also starts waking the server
  while the user types.
- If no results arrive within 5 s (`SLOW_START_MS`), it shows "Waking up the search
  server…" above the loading placeholders.
- Requests time out after 150 s (`REQUEST_TIMEOUT_MS`), showing "Search timed out"
  with a retry button.

## Deploy on Vercel at arxiv.agarwal-labs.com

1. In Vercel, import the GitHub repo and set **Root Directory** to `web`
   (framework preset: Other, no build command). `vercel.json` sets `ignoreCommand`,
   so pushes that don't change `web/` (for example, backend commits) skip the
   deploy.
2. No config change is needed for production: `config.js` uses `live` mode on any
   host other than localhost. Until `/api/*` exists, the page shows a "Coming soon"
   badge and searches say "Search is coming soon". It starts working as soon as
   the API answers, without a redeploy.
3. In the Vercel project, add the domain `arxiv.agarwal-labs.com`, then add the DNS
   record Vercel shows at your domain registrar (a `CNAME` from `arxiv` to
   `cname.vercel-dns.com`).
4. Serve the API under `/api/*` on the same origin, either as Vercel functions or
   with a rewrite in `vercel.json` to a separately hosted backend, for example:

   ```json
   "rewrites": [{ "source": "/api/:path*", "destination": "https://<backend-host>/api/:path*" }]
   ```

   Same-origin serving avoids CORS. API keys stay on the backend; nothing secret
   belongs in this folder.

### Live production (search + AI answers)

The live site is a full-stack bundle (static `public/` + Python `api/index.py` +
`artifacts/`) deployed to the `arxiv-search-web` project. Build it in a new folder
(for example `data\serving\production-live-v1\web\`) from the last exported
release: copy `artifacts/`, copy the current `RUNTIME_FILES` from
`arxiv_search/serving/export.py` and refresh `runtime_sha256` in the manifest, copy
the web assets into `public/`, and build `vercel.json` the way `export.py` does.
Check it with `Release.load` in a venv pinned to `requirements.txt`.

Production needs these Vercel variables (Production environment):
`OPENAI_API_KEY`, `KV_REST_API_URL`, `KV_REST_API_TOKEN` (Upstash), and
`ARXIV_ENABLE_PAID_CALLS=production-daily-v1`.

Guards (in `arxiv_search/serving/budget.py`, `DailyBudget`):

- **$5/day** of reserved (worst-case) OpenAI spend per UTC day (Preview: $1/day,
  separate counters). Reservations are never refunded, so this is an upper bound
  on real spend.
- **Per-visitor limit**: 10 searches/minute and 30/day per hashed client IP; returns
  429 with `Retry-After`.
- When the daily budget runs out, search still works: results fall back to keyword
  (BM25) matches (`meta.stage: "lexical"`) and the page says AI answers return
  after midnight UTC.
- Paper chat AI stays off (`PAPER_API_ENABLED: false`); the workspace shows the PDF.

Rollback: promote the static showcase deployment `dpl_HQ6M7DRQ8LzQPxKAJYGK25tkiB2X`.

### Content-Security-Policy

`vercel.json` only allows scripts, styles, fonts, images and API calls from the site
itself. If the API moves to another origin without a rewrite, add that origin to
`connect-src`. If you add analytics or a web font host, add them to the matching
directive.

## Design

The research workspace uses a two-pane layout after the first search (default;
`?layout=classic` keeps the old single column). The landing page is unchanged.
On screens at least 1000px wide, ranked sources sit on the left (about 36% wide,
420–640px) and the AI answer on the right; each column scrolls independently.
Discuss paper replaces the answer with the PDF + chat workspace. At 1280px and
wider, the left column shrinks to a title list with the open paper highlighted,
and clicking a title switches papers (modifier-clicks still open arXiv).
"← Back to answer" returns to the answer. Hovering a citation chip highlights its
source.

Two draggable dividers (results | answer/paper, PDF | chat) are keyboard
accessible (`role="separator"`, arrows, Shift+arrows, Home/End) and reset on
double-click. Widths are stored in `localStorage` (`arxiv.split.left`,
`arxiv.split.leftPaper`, `arxiv.split.chat`) and clamped by CSS so panes stay
usable after window resizes. Below 1000px the page stacks: search, answer, sources.

It uses the Clawpilot warm neutral tokens and Segoe UI typography, with
restrained accent use and a responsive mobile layout. The homepage
heading is 30px (26px on small screens), and the default composer is 58px tall.
Decorative badges, marketing copy, duplicated visible question headings and heavy
paper cards are removed. A disabled answer occupies one short inline notice,
not an empty answer panel. Agarwal Labs navigation remains.
The early external `theme.js` defaults to the light palette regardless of OS
theme. The header sun/moon toggle switches instantly and saves the choice in
`localStorage` (`arxiv.theme`); `?clawpilotTheme=light|dark` overrides both and
the toggle keeps that URL parameter in sync. Keeping this script
external preserves the existing CSP without allowing inline scripts.

Enter submits the question; Shift+Enter inserts a line break. The New question
button aborts the current browser request and resets the workspace. Each question
is independent: there is no session memory, saved history or follow-up rewriting.
Conversational memory is planned as a separate backend/API feature, not simulated
by the layout. Provider requests already started may still consume their reservation.
Unavailable AI answers are shown as a neutral state, not a red error, and don't
trigger a summary request. Citation focus, full-abstract expansion, the additional
results disclosure, fallback notice and corpus/privacy disclosures are preserved.

The existing favicon and social preview retain their earlier branding; they are
not regenerated by this layout change.

## Link previews and icons

`index.html` has Open Graph and Twitter tags pointing to
`https://arxiv.agarwal-labs.com/og-image.png`. To change the preview image or touch
icon, edit the HTML source in `scripts/` and re-render it with Edge headless:

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --hide-scrollbars --virtual-time-budget=5000 --window-size=1200,630 `
  --screenshot="$PWD\web\og-image.png" "file:///$($PWD -replace '\\','/')/web/scripts/og-image.html"
```

Use `--window-size=180,180` and `apple-touch-icon.html` for the icon. The preview
image shows the paper count (23,304); update it if the corpus changes.

## Accessibility

The previous layout was checked with axe-core (WCAG 2.1 AA plus best practices)
with no violations. That result does not certify the redesigned workspace. Notes:

- Status changes (searching, waking up, results found, summary ready, errors) are
  announced through one polite live region, `#sr-status`, rather than reading out
  the whole results list.
- Citation chips scroll to the cited paper and move keyboard focus to its title.
- "How it works" is a native `<dialog>`, so focus trapping and Esc come from the browser.
- Animations are disabled under `prefers-reduced-motion`.
# Public design showcase

Sid approved publishing the latest design to
[arxiv.agarwal-labs.com](https://arxiv.agarwal-labs.com) on November 5.
Production deployment `dpl_GNzHWRsNG1ucJtMW29AGJ7ixZDpi` (superseded by the
two-pane layout release; see below) contains static
allowlisted assets only: no backend, credentials, corpus vectors or operator
code. The protected search and preparation deployments are unchanged.

The public package sets `SHOWCASE_ONLY: true`: search always uses the existing
1,500-paper sample, even with an `?api=` override. Paper actions always use the
illustrative demo, regardless of the paper API flag. UI labels identify the
sample and placeholder answers. The reading pane embeds the original PDF directly
from arXiv (`frame-src https://arxiv.org`); paper AI is not connected.
Questions remain in browser memory and no search, paper-fetch or provider API
requests are made. Static asset requests, the embedded arXiv PDF and explicit
external-paper links are still normal browser network activity.

Build a new package with:

```powershell
node web\scripts\package-showcase.mjs <new-output-directory>
```

The production Vercel project `arxiv-search-web` has root directory `web`, so
place this static package inside a deployment root's `web` subdirectory. Do not
deploy the whole repository. Source config remains non-showcase for isolated
serving exports; only the static package changes the flag. Publishing requires
explicit approval, as do commits and pushes.

Validation: 19 Node tests passed; the published assets match the reviewed
package. Hosted browser checks verified sample search returns ten results and
Discuss paper opens the mock reader/consent flow with no API/provider/arXiv
requests. `/api/meta`, `/api/paper/open`, backend source and `.env` return 404.

## Preparation-only protected Preview

## Local split-workspace UX prototype

The local no-model prototype adds a small chat icon plus **Discuss paper** on
each result; title and PDF links still open the original paper separately.
Desktop expands only the paper workspace to a reader/discussion split while
search stays 720px wide. Mobile uses Read/Discuss buttons, preserving the same
conversation and reading position. Back restores search results, focus and
scroll.

The next local iteration replaces the mock reading sections with a native
**original PDF viewer**. Clicking **Discuss paper** loads the PDF automatically;
there is no proxy, server-side PDF copy or automatic model call. Unknown revisions
use arXiv's latest PDF with a revision-mismatch warning; prepared papers bind to
the server-returned positive integer version. The frame source is constructed
only from a validated paper ID/version, never arbitrary URLs. CSP allows frames
only from `https://arxiv.org`; script/connect/object restrictions stay unchanged.

**PDF not displaying?** removes the frame and shows an external-open fallback;
**Restore PDF viewer** is explicit. No unreliable iframe load event is treated
as proof of PDF rendering. Browser-native controls provide pages, zoom and
download where supported; mobile PDF support varies. The direct generic demo
has no selected document, so use a search result to try this viewer.

Visible PDF content is distinct from AI context coverage. Shortcuts are
**Summarize this paper**, **Method**, **Datasets & benchmarks**, **Results** and
**Limitations**. There is no structured-property extraction, visual plot
analysis, fake citation or invented result. Real citation links continue
opening validated original source locations externally.

**Agreed live flow (Sid, Nov 5; not yet implemented):** no Start/Inspect
buttons. Clicking **Discuss paper** loads the PDF and automatically prepares
the paper (fetch/extract, no model call) and shows a one-line coverage status
such as "AI can read: main text · Appendix C omitted". The model runs only when
the user submits a question or taps a shortcut; "Summarize this paper" replaces
the automatic opening overview. This requires a backend contract change: today
`/open` generates the overview, so the first question must instead open the
session. Coordinate with the backend chat before wiring; the current real
controller still uses the explicit prepare → open → chat flow.

The reader is edge-to-edge with a compact AI-status/Open PDF toolbar. Revision,
privacy, coverage and browser-control explanations live under a collapsed
**Document & AI details** disclosure. The PDF fills the remaining reader height
(76dvh desktop, capped at 960px; 72dvh mobile), without a second outer document
scrollbar. Expanding details or updating discussion does not remount the viewer.

This PDF iteration is local only, not part of the production deployment recorded
above. Models and paper API flags remain disabled.

Validation: 21 Node tests pass. Browser checks rendered the actual 22-page
RouterArena v3 PDF beside discussion, including under the frame/script/connect/
object CSP restrictions. At 390px, Read/Discuss switching and the external-open
fallback worked without horizontal overflow. No API/provider calls were made.
After the auto-load/compact-toolbar revision, measured PDF area occupies 91%
of the reader body on desktop and 89% at 390px. Details are collapsed initially,
discussion updates preserve the mounted frame, and fallback/restore still work.

Use `?paperDemo=1` for the direct workspace; use `?mock=1` and explicitly submit
a query to test the search-to-paper flow without API/model calls. Source flags
remain disabled. The split design is now published as the static showcase above,
not as live paper conversation.

Validation includes 18 Node controller/DOM tests, plus browser DOM/computed-layout
checks at desktop and 390px mobile widths: no horizontal overflow, Read/Discuss
visibility, fallback state, demo section focus, result-return focus and no
paper/provider network calls. Browser screenshots were blank in this environment,
so screenshot-based visual review is not claimed.

The November 5
[paper preparation Preview](https://arxiv-serving-preview-hhkbt9wxu-stealthymonkeys-projects.vercel.app/?paperDemo=1&preparePaper=2510.00202)
allows an explicit paper preparation and inspection of source, version, coverage,
omissions and real arXiv locator links. AI overview and conversation are disabled;
the existing search Preview and production are unchanged. Sign in to Vercel to
view it. Loading its direct paper URL does not fetch or admit a preparation.

`--prepare-preview` changes only exported frontend flags to
`PAPER_API_ENABLED: true` and `PAPER_PREPARE_ONLY: true`. Source defaults stay
false. The UI does not offer Continue in preparation-only mode; the server also
blocks open/chat independently. The namespace has temporary capped preparation
capacity, not an approved paid conversation budget. Prepared text retention is
at most 24 hours. This is not a deployed AI-memory claim.

### Live paper chat ("Discuss paper")

Opening a paper calls `POST /api/paper/context {arxiv_id}` (no model call): the server reads the
arXiv HTML (falling back to PDF text, then the abstract), caches it for 24 h, and the Discuss pane
shows what the AI can see. The first question starts the conversation, with no consent step:
`POST /api/paper/ask {arxiv_id, question, history:[{user, assistant}]}` makes one gpt-6-luna call
reserved against the same $5/day budget as search (about $0.002–0.004 per question). Answers
cite sections (`§6.5`, `p. 3`, `Abstract`) that link to the arXiv HTML/PDF.

- Limits: 10 questions per paper per conversation (browser), per visitor 10 papers/min and 60/day,
  8 questions/min and 40/day (server).
- Only corpus papers can be discussed. History is held in the tab and sent with each question.
- Kill switch: set `ARXIV_PAPER_CHAT=off` (Production) and redeploy; search keeps working.
- Bundle: `data/serving/production-d50-v1/web` (release `d36-d50-d49-serving-f16-v4`, production
  `dpl_DQ3TxYoPTkXaVHfx9abtKPJ1dVkB`): Decision 50 top-20 step (GPT-5.4 scores twice, ordered by
  the average, rank 1 pinned, no RRF blend), plus cold-start warm-up.
  Rollback: promote `dpl_5vaRfXRvEp3JH6Sy3NxMv95GhUwF` (Decision 47, tracing),
  `dpl_F7pFDG6ffq77WDU5sM6moY9cJaDq` (paper chat, no tracing) or
  `dpl_8t8ePANSueEEyqsCsLZ1SdmudtvY` (search + answers, no paper chat).

### Cold starts and latency

On Vercel, `http.py` loads the release, the BM25/vector index and does one TLS handshake with
OpenAI (no request, nothing billed) at import time, so the page's `/api/meta` call warms the
instance before the first search. Warm search is about 5 s: embed ~0.3–0.9 s, retrieve ~0.4 s,
top-50 rerank ~1.5–2 s, top-20 GPT-5.4 refine ~2–2.5 s. The two LLM stages are sequential.
The Hobby plan only allows daily crons, so there is no keep-alive ping.

### Tracing (LangSmith)

`arxiv_search/serving/tracing.py` sends one trace per search, summary, paper-context and paper-ask
request (`/api/meta` is not traced), with child spans for embed-query, retrieve, rerank/refine
(and each LLM scoring call), answer, load-paper and paper-answer, including latency and tokens.
Abstracts and visitor identifiers are not logged; queries, questions, answers and paper ids are.

- Enabled only when `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set and the optional
  `serving/runtime-tracing-requirements.txt` packages are installed. SDK failures never change responses.
- Env vars: `LANGSMITH_TRACING`, `LANGSMITH_ENDPOINT`, `LANGSMITH_API_KEY`,
  `LANGSMITH_AGENT_ID=arxiv-search`, `LANGSMITH_AGENT_ENVIRONMENT` (`production` on arxiv-search-web,
  `staging` on arxiv-serving-preview, `local` in `.env`). Runs land in project `arxiv-search-<environment>`.
- Each traced request flushes before responding (~65 ms warm, ~1 s on a cold start).
- Disable: set `LANGSMITH_TRACING=false` and redeploy.
