# Web UI

A single search page: the user types a query, sees the top papers from retrieval,
then an AI summary of those papers with clickable `[n]` citations. A notice under
the search bar explains what the index does and doesn't cover.

Plain HTML/CSS/JS (ES modules), no build step and no dependencies.

| File | Purpose |
|---|---|
| `index.html` | Page structure, limitations notice, result template |
| `styles.css` | Theme matching agarwal-labs.com, layout, loading skeletons |
| `app.js` | Search flow, URL state (`?q=`), rendering, citations, keyboard shortcuts |
| `api.js` | API client plus a mock that follows the same contract |
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

Agreed with the backend chat on 2026-11-03. The backend isn't built yet. The page
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
{ "query": "...",
  "results": [{ "rank": 1, "arxiv_id": "2510.00027", "title": "...",
                "authors": ["first 10 only"], "authors_truncated": false,
                "abstract": "full text", "primary_category": "cs.LG", "categories": ["cs.LG"],
                "submitted_month": "2025-10", "url": "https://arxiv.org/abs/2510.00027" }],
  "meta": { "stage": "reranked", "stage_detail": "...", "fallback": false, "latency_ms": 2900 } }
```

- The page asks for 20 results in one request. It shows the top 10 and puts ranks
  11-20 behind "Show more results", labeled as unmeasured (quality is measured
  with nDCG@10).
- `stage: "retrieval"` with `fallback: true` means the reranker failed, timed out
  or ran out of budget. The page shows a subtle note, not an error.
- `latency_ms` is shown for information only; the page shows a spinner and never
  promises a wait time. `stage_detail` appears as a tooltip on the result count.

`POST /api/summary` with `{ "query": str, "arxiv_ids": [str] }` (the top 10, in
rank order) returns the summary:

```json
{ "summary": "Paragraphs separated by blank lines, citing papers as [1] or [1, 3].",
  "cited": [1, 3], "grounded": true, "model": "...", "latency_ms": 1800 }
```

- `[n]` markers are 1-based positions in `arxiv_ids`. A marker becomes a clickable
  chip only if every number in it is in `cited` and in range; anything else stays
  plain text.
- `grounded: false` means the model abstained. The page shows "No answer found in
  these abstracts" and keeps the results.
- The summary is a separate request so results appear first. If it fails, the
  results stay on screen with a short message.

Errors return a non-2xx status with `{ "error": { "code": str, "message": str } }`.
The page maps each code to its own wording:

| Code | Search | Summary |
|---|---|---|
| `rate_limited` (429 + `Retry-After`) | "Too many searches", with the wait time and a retry button | Generic "summary isn't available" |
| `budget_exhausted` | "Daily limit reached", no retry | "Summaries are paused for today" |
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
- Requests time out after 90 s (`REQUEST_TIMEOUT_MS`), showing "Search timed out"
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

### Content-Security-Policy

`vercel.json` only allows scripts, styles, fonts, images and API calls from the site
itself. If the API moves to another origin without a rewrite, add that origin to
`connect-src`. If you add analytics or a web font host, add them to the matching
directive.

## Design

The page deliberately matches the main site, agarwal-labs.com, so moving between the
two doesn't feel like a different product. `styles.css` copies its tokens exactly:
`--paper` `#fdfdfc`, `--ink` `#272b29`, `--muted` `#656c68`, `--link` `#285b4c`,
`--line` `#dfe3df`, plus the system serif stack (Iowan Old Style, Palatino), the
700px column, the masthead with a hairline rule, underlined green links, and the
outlined button style. It is light-only, like the main site. If the main site's
tokens change, update the `:root` block at the top of `styles.css` and re-render the
images in `scripts/`.

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

Checked with axe-core (WCAG 2.1 AA plus best practices) on the home page, results and the "How it works" dialog: no violations. Notes:

- Status changes (searching, waking up, results found, summary ready, errors) are
  announced through one polite live region, `#sr-status`, rather than reading out
  the whole results list.
- Citation chips scroll to the cited paper and move keyboard focus to its title.
- "How it works" is a native `<dialog>`, so focus trapping and Esc come from the browser.
- Animations are disabled under `prefers-reduced-motion`.
