# Serving API and Vercel packaging

## Status and boundaries

**Current production:** `https://arxiv.agarwal-labs.com` serves the UI and Python
API on Vercel, using D36 retrieval, D50 reranking and D49 Luna summaries
(`release-v4.json`). Paper discussion uses the stateless `/api/paper/context`
and `/api/paper/ask` routes. Existing server-side daily budgets, visitor limits,
API keys and optional tracing remain deployment environment settings.
The preview-only descriptions below record earlier implementation stages.

### Deploy only committed source

The public domain is served by an exported backend bundle, not just `web/`.
A direct CLI upload can publish local files without pushing them to GitHub;
this caused production to run source missing from `main`. Reconcile source through
a PR before deploying. Never deploy a static `web/` checkout over the API site.

1. Merge the reviewed PR, check out the merged revision, and verify a clean
   `git status --short` (including untracked source).
2. Use an isolated environment with the pins in
   `runtime-paper-requirements.txt` and `runtime-tracing-requirements.txt`.
3. Export to a new ignored directory, using cached vectors only:
   `python -m arxiv_search.serving.export --spec serving/release-v4.json --include-paper --include-tracing --output data/serving/<new-release>/web`.
   The CLI refuses dirty source; the manifest records the source commit and
   runtime/artifact checksums. No embedding or model calls occur during export.
4. Link that bundle to the existing Vercel `arxiv-search-web` project, deploy a
   preview, then production after validation. Keep its existing environment
   variables, budget settings and custom domain; do not copy credentials into Git.
5. Verify `/api/meta` reports D36/D50/D49, compare the deployed public assets with
   the export, and check paper UI and response headers. A real uncached search
   incurs model cost and requires explicit approval.

Keep the previous production deployment available for rollback. Deployments
must originate from the committed exporter; do not hand-patch packaged source.

The serving foundation is implemented and deployed to a separate protected
Vercel Hobby preview, not the production domain. It exposes the existing
frontend contract: `GET /api/meta`, `POST /api/search` and `POST /api/summary`.
Tests inject deterministic model adapters. Real retrieval uses the existing BM25,
shortlist score reordering and RRF helpers; it does not import experiment runners
at request time.

**Live embedding and reranking adapters are implemented for the protected trial.**
Every OpenAI attempt reserves shared tokens/cost in Redis before network access,
with no retries or refunds. The default remains disabled; `ARXIV_ENABLE_PAID_CALLS=1`
still fails closed. The explicitly approved `protected-trial-v1` and
`protected-trial-v2` and D49-only `protected-trial-v3` settings are accepted
only in Vercel Preview and only with an explicitly pinned release configuration, a
provisioned ledger, offline tokenizers and a server-side OpenAI key.
`release-v2.json` enables Decision 47 refinement and Decision 48 cited answers.
`release-v3.json` preserves that ranking and selects Decision 49:
`gpt-6-luna`, shared `answer.VERSION_V2` / `answer-v2`, 1,200 output tokens.
`release-v1.json` retains the Decision 46/no-answer control for rollback.
There is no silent substitution of demo results or another embedding model.
This is not a finished public deployment. The production website is unchanged.

The approved compact UI was validated November 4, 2026:
[Decision 46 deployment](https://arxiv-serving-preview-i7412c80q-stealthymonkeys-projects.vercel.app).
The latest [Decision 47/49 preview](https://arxiv-serving-preview-kcti5xjp2-stealthymonkeys-projects.vercel.app)
preserves that layout. Hosted metadata confirms release `d36-d47-d48-serving-f16-v2`
was superseded by `d36-d47-d49-serving-f16-v3`, with fingerprint
`7e43742506ef2ddfa41f6d8d09ba76a0ab1608bf902e308bd2a1b8e352c20f99`
and `gpt-6-luna` / `answer-v2`.
The frontend responds successfully; missing answer tokens are rejected before
provider access; runtime source, manifest and removed operator routes return 404.
The temporary operator deployments were deleted. Offline validation passed 250
tests, including a complete six-attempt fake-transport flow and replay denial.
Browser fixtures verified token forwarding, ordered top-ten evidence, citation
focus, abstention/error result preservation and the compact mobile composer.
No live model calls were made for this integration. The read-only hosted ledger
check at 21:06 UTC on November 4 showed the second trial already at 2/2 searches,
11/12 calls, 157,143/200,000 tokens and $0.14351481/$0.50 reserved cost. Thus
zero v2 searches remain, contrary to the earlier one-remaining handoff.
There was no reset, increase or accounting mutation. The original trial counters
also remained unchanged. Sid subsequently approved the separate v3 trial below.
Sign in to the Vercel account to view it. The preview intentionally retains
Vercel Authentication; the production domain is unchanged. The OpenAI key and
activation setting are scoped to Preview only.

The research code, labels and experiment outputs are not changed by serving.
Export reads the existing corpus and document-vector cache only. It never embeds,
repairs caches, evaluates held-out queries, or reads `.env`.

## Paper conversation: offline integration, not activated

### November 5 preparation-only hosted verification

Sid separately approved an isolated Redis infrastructure check and a protected
Preview with all model calls disabled. The resulting
[preparation-only Preview](https://arxiv-serving-preview-hhkbt9wxu-stealthymonkeys-projects.vercel.app/?paperDemo=1&preparePaper=2510.00202)
has fingerprint
`dd4d29f9440f33f4091b6e4e58abb9789d510abc7cfded3529962f83b87246a4`.
It is a separate immutable deployment, not a promotion or replacement of the
existing D49 search Preview or production.

The explicit `--include-paper --prepare-preview` package enables preparation
only. Its application factory ignores paid-search environment flags and supplies
a disabled embedder; `/paper/open` and `/paper/chat` reject before session or
model admission. The UI displays "Preparation-only Preview", permits explicit
preparation and coverage inspection, and withholds the overview action. Opening
the direct paper URL never prepares automatically. The ordinary exporter/default
application and source frontend flags remain disabled.

Hosted preparation resolved RouterArena `2510.00202v3` from the corpus and
retrieved HTML, selecting 12,400 evidence tokens with actual section anchors,
reference omission and captions-only figures. No model was called. This is one
successful preparation, not an availability or latency guarantee.

Redis verification used synthetic text and a fake provider in a UUID-isolated
namespace: durable context roundtrip/expiry, concurrent duplicate open/follow-up
denial, exactly-once turn decrement, signed-history replay denial, logical session
expiry and metadata TTL preservation passed. Temporary check keys were removed,
and both temporary operator deployments were deleted. HGETALL snapshots of all
three search ledgers were normalized by field before comparison and unchanged
across the successful verification. No real provider requests or search ledger
reservations were made.

The separate preparation-only namespace
`arxiv:paper:prepare-preview-20261105-v1` was explicitly created once with a
24-hour expiry and a 20-preparation total cap (five per minute). It is **not a paid
paper-chat trial**. Its opening/provider paths are blocked independently of these
infrastructure counters. CAS preserves an existing TTL with `KEEPTTL`; it never
renews the expiry. Missing/expired state fails closed. Prepared contexts expire
within 24 hours. A fresh signing key is confined to this deployment's environment,
not source or frontend assets. Overview caching remains unavailable.

Validation: **444 Python tests and 18 frontend tests passed**. Authenticated CLI
checks verified hosted release metadata, preparation and blocked overview.
The integrated browser encountered Vercel's login protection; the same exported
UI was checked locally using a representative coverage fixture, including
explicit preparation, coverage links and absence of an enabled overview/chat
action. No claim is made of an authenticated hosted-browser session. Sign in to
Vercel to inspect the protected Preview yourself.

### Offline implementation boundary

Sid authorized offline serving/frontend implementation on November 5. This does
**not** authorize a deployment, model call, new ledger, budget increase or search
trial reuse. The existing hosted Preview and production remain unchanged.

The local WSGI boundary now recognizes `/api/paper/prepare`, `/api/paper/open`
and `/api/paper/chat`, but its default application has **no paper adapter**.
It returns an explicit disabled error without loading search/model adapters.
Tests may inject `PaperService`; there is no environment activation switch.

The flow is deliberately split:

1. Explicit **prepare** resolves a corpus-allowlisted paper revision and selected
   context. It consumes only a separately capped/rate-limited preparation
   entitlement, not a session or provider reservation. It returns source,
   actual locators, omissions/warnings and a ten-minute signed preparation.
   All sources require consent, including abstract-only fallback.
2. Explicit **open** verifies the exact stored context and consumes that
   preparation once. Session creation and any overview reservation are one
   atomic admission. A revalidated exact overview-cache hit admits a session
   without model cost; no cache backend is configured by default. A miss or
   unavailable cache can generate only through this explicit admitted action.
3. **Chat** validates the complete signed overview and exchange chain before
   selecting model memory. The overview is index zero, separate from ten
   follow-ups. Replies include the actual attempt index, signature, server
   limits and retained-memory counts. Sessions expire after thirty minutes.

`paper_state.py` implements optimistic compare/exchange using one atomic Redis
Lua operation. Its distinct `arxiv:paper:*` namespace contains policy,
preparation/session identifiers, counters, expiry, in-flight markers and reply
hash chains, **not conversation text**. The runtime cannot initialize/reset it.
`PaperPolicy.initial_state()` produces operator/test data only; it is not an
approved live policy. Policy-bound metadata is non-expiring and bounded to 48 KB;
logical preparation/session expiry prevents use after expiry, while retaining
replay markers. Metadata exhaustion fails closed before provider work. Cleanup,
policy retention and real Redis integration verification remain activation
prerequisites. Preparation has a separate policy-bound rolling window and total
cap, not a claimed daily/per-IP limit.

`paper_content.py` is a private Redis context adapter with a 24-hour TTL,
separate from transcript metadata. It stores extracted paper context, never
serves full text to the browser and verifies exact content/cache identity.
Its Redis connection needs an explicitly enlarged bounded response limit
(`RedisREST(..., max_response_bytes=12000100)`) for JSON-escaped context blobs;
the existing search connection retains its 64-KB default. Storage access and
paper-specific reuse/retention policy must be approved before live wiring.
No process-local content/session fallback is supplied by the production code.

The service sends only the separately constructed `paper_chat` payload, not the
search-summary whitelist. The core currently has no overview-baseline argument;
the serving adapter adds the verified overview as untrusted `history_baseline`,
then rebudgets baseline plus whole exchanges together to 3,000 tokens and the
entire encoded request plus 4,096 framing tokens to 32,000 input tokens.
It retains at most six exchanges, reserves the full 1,200-token output at
uncached Luna rates, and assumes no prompt-cache discount. Supply the pinned
offline `TokenCounter.count_paper` (`o200k_base`) counter; synthetic test counters are not production
reservation evidence.

### Retry and failure semantics

- Each action has a request ID, reused on retry. Completed duplicates return
  `already_completed` (409), never another answer/model call. The browser must
  retain the original response; there is no response/transcript cache to recover
  a lost reply. Starting over is a separate explicit action, not an automatic retry.
- A request still inside its in-flight deadline returns `session_busy` (409).
  A known transport failure or elapsed in-flight deadline returns
  `outcome_unknown` (409) for the same ID. A different request
  racing with either state returns `session_busy` (409). Unknown provider outcomes remain
  blocked for that session; expiring a lease never authorizes another call.
- Local question/history/context failures do not debit a paid turn. Once
  admission reserves provider work, the turn stays used on timeout or invalid
  output. A known invalid output is terminal for that request and allows a new
  explicit question with the prior signed chain and updated quota.
- Missing/changed context requires preparing and consenting again. It never
  silently refetches another revision, degrades source or renews a session.
- Valid locators are not proof of factual faithfulness. Figure images are not
  supplied; PDF extraction may retain references and degrade equations. Coverage
  warnings must remain visible.

Offline packaging is opt-in via `--include-paper`, using the separate pinned
`runtime-paper-requirements.txt`. It checksums the core and adapters but still
exports a **disabled** default application. It does not activate calls, provision
state or alter the existing release specs. Real hosted extraction latency,
provider quality, Redis concurrency and infrastructure costs are unmeasured.

Offline validation for this milestone: **439 Python tests and 18 frontend tests
passed**, including an actual frontend controller against a local deterministic
WSGI service. Loader tests use injected downloads, not arXiv network requests;
provider tests use fake responses. The opt-in `ArxivTransport` restricts requests
to fixed HTTPS arXiv paths, rejects redirects/proxies and bounds reads/timeouts.
Current extraction is non-preemptive: deadline checks reject results before/after
parsing but cannot interrupt a parser mid-call. A hard hosted wall-clock guarantee
therefore remains unverified and requires bounded worker isolation or core
cancellation support before claiming an SLA.

## Swapping models and new development releases

`release-v1.json` explicitly selects Decision 36 retrieval and Decision 46
reranking. It is not automatically updated from development configuration.
`release-v2.json` deliberately selects Decision 36/47/48. Both specs remain
explicit; export defaults to v1 unless `--spec serving\release-v2.json` is supplied.

Decision 46's two parallel 0-4 scoring passes cover the top 50; averaged scores
are fused with retrieval using RRF c=30. Decision 47 adds two parallel 0-10
passes over that order's top 20, using `refine20-v1`. Their average is fused with
Decision 46 order using RRF c=30; Decision 46's first paper is restored to rank 1,
and ranks 21+ are unchanged. Refinement failure, including budget exhaustion,
retains Decision 46 order with `stage: "reranked"`, `fallback: false`,
`refined: false`. Decision 46 failure still falls back to retrieval order.

The latest answer release uses the approved Decision 49 code from `727413d`
plus the backend's subsequent extraction of `final_parts` / `structured_text`
into stdlib-only `answer.py` (reexported unchanged by `openai_answer.py`).
Serving uses those same helpers to select final-answer text, excluding GPT-6
commentary drafts; incomplete, duplicate, missing or invalid final answers fail
explicitly. `answer.validate(..., ungrounded_may_cite=True)` implements Contract B:
an abstention may cite closest papers without claiming they answer the request.
The UI labels these citations "Closest results". D48 retains Contract A and its
700-token mini configuration as a rollback option.

Luna's conservative reservation uses the full JSON tokenizer count plus 4,096
framing tokens and all 1,200 output tokens, at 100/500 nanodollars per input/output
token (matching `openai_answer.PRICES`). Its dollar reservation is lower than
mini's; its output-token reservation is 500 tokens higher, not lower. It still
must fit the same remaining trial token ceiling before any network request.
The total-trial v2 ledger, counters and limits are unchanged by this release.

### Third protected trial and duplicate-search investigation

Sid approved a separate D49-only third trial, not a reset: 2 searches, 12 provider
attempts, 200,000 reserved tokens and $0.50 estimated cost. Its fixed key is
`arxiv:trial:arxiv-e2e-2026-11-04-v3`; activation is `protected-trial-v3`, restricted
to Vercel Preview with Decision 47 ranking and Decision 49 answers. Runtime
composition reads status only and never provisions. v1/v2 remain untouched.

Read-only Vercel request logs explain the v2 counter discrepancy: two browser
POSTs to `/api/search` at 19:38:57.304 UTC and 21:03:39.449 UTC on November 4,
both HTTP 200. Only the first had a subsequent valid `/api/summary` request.
The second immediately followed a GET of the page and revalidation of its JS/CSS
assets. Eleven model reservations are consistent with one six-attempt interaction
plus another five-attempt search. The summary ticket Lua does not increment
search/call/token counters; only an embedding reservation starts a search.

The old frontend automatically ran `?q=` on startup and `popstate`. Loading and
reloading the immutable old frontend with fake fetch reproduced the extra
admission. The fixed frontend restores the question without spending; submit
must be explicit. A pending-flow guard also blocks repeat Enter/form/example
submissions. Browser fixtures showed zero load/reload/history requests and
exactly one search plus one summary under repeated in-flight submissions.
This is a navigation-triggered spending bug, not evidence of React strict mode
(there is no React), simultaneous double-submit or summary double-accounting.
Logs do not distinguish a reload from reopening a query URL, and the original
ledger stores hashed attempt markers, not query text, timestamps or request IDs.
Do not claim a more precise gesture or query identity than these records prove.

The read-only v2 record check found eleven reserved attempt markers, two summary
tickets and exactly one consumed ticket, corroborating two searches and one
answer attempt. Full HGETALL snapshots of v1 and v2 were compared before/after
the operator action and were unchanged (no raw marker hashes or bindings were
returned). v3 was provisioned once at 21:45 UTC with all usage counters zero:
**2 searches, 12 attempts, 200,000 tokens and $0.50 remaining**. Guard concurrency,
token/cost/call ceilings and one-use tickets passed in separate verification
namespaces without any model calls or real-trial reservations. Clean deployment
metadata confirms the fingerprint above; hosted JavaScript matches the offline
tested source byte-for-byte; the operator endpoint is 404 and the exact temporary
deployment was deleted. Runtime never provisions or resets. Production is unchanged.

Answers use `gpt-5.4-mini-2026-03-17` and shared `arxiv_search/answer.py`
(`answer-v1`), not a second copy of the answer prompt. Only the shown top ten
abstracts and their title/author/month metadata are evidence. The shared validator
enforces bounded, grounded citations and abstention; API fields remain
`summary`, `cited`, `grounded`, `model`, `latency_ms`. This serving combination
has offline integration tests, not a new quality evaluation. Research-reported
cost and latency are not serving guarantees.

The serving interfaces in `arxiv_search/serving/service.py` separate:

- query embeddings (`Embedder`, including provider, model, dimensions and text recipe);
- retrieval (`LocalRetriever`, loading packed BM25 and exact NumPy vectors);
- reranking (`Reranker`, per-pass candidate scores);
- cited answers (`Summarizer`, an answer and explicit grounded/citation fields).

A new provider implements the appropriate interface; application wiring selects
it. Changing storage/retrieval means replacing `LocalRetriever` in the composition,
not changing the frontend response schema. This version supports one explicit
retrieval adapter, not an unrestricted plugin registry.

Document vectors and query embeddings must share the same identity and dimensions.
Changing embedding models requires a separately approved embedding artifact build;
it is never just an environment-variable rename. The cache-only exporter currently
supports the existing OpenAI-large 3,072-dimensional document cache. A new vector
format/provider needs an exporter adapter as well as a query adapter.

Each export contains:

- corpus, full-dimension float16 vectors in the same row order, and prebuilt BM25 postings;
- SHA-256 checksums of the artifacts and copied runtime source;
- exact runtime dependency versions, model/prompt settings and source commit;
- a release fingerprint used to namespace every adapter cache key.

Vector arrays are split into ordered 4,096-row NumPy shards to stay below the
observed 100 MB per-file upload limit (about 25 MB per float16 shard). The corpus
is stored with lossless gzip compression. Loading verifies all file checksums and
shard shapes before assembling a read-only vector matrix in corpus order.
Single-file vector releases and uncompressed corpus releases remain readable.

Runtime loading rejects changed artifacts, source files, dependencies, or an
incompatible embedding adapter. Keys distinguish reranking passes and summary
paper order. Adapters receive cache keys; a durable cache is **not implemented yet**.
Never reuse the local research SQLite spending ledger as a serverless global guard.

## Approved protected-trial budgets

The original trial approved at most **5 searches, 100,000 reserved tokens and $0.50 estimated
model cost**, stopping at the first ceiling. The guard adds a maximum of 20 model
attempts. A complete v2 interaction uses six attempts: one embedding, two
Decision 46 passes, two refinement passes and one answer. These
are total trial limits, not daily limits or production rate-limiting policy.

`arxiv_search/serving/budget.py` uses the Upstash REST variables
`KV_REST_API_URL` and `KV_REST_API_TOKEN`, supplied as secrets in the preview
environment only. Credentials and queries are never stored in the accounting
hash. Unique attempt IDs are hashed. One Lua operation atomically checks every
ceiling, prevents duplicate attempts and reserves tokens/cost before a call.
Failed or uncertain provider attempts must keep their reservation; there are no
refunds or automatic retries. Embeddings reserve cl100k tokens at $0.13/M.
Each LLM call reserves the larger of cl100k/o200k counts of its entire JSON payload,
4,096 framing tokens, and its full output cap (1,024 for Decision 46, 512 for
refinement, 700 for answers) at $0.75/M input and
$4.50/M output. Prices were checked against OpenAI's pricing page on November 4,
2026. Runtime tokenization uses checksummed, bundled vocabularies, never a download.
Actual provider usage is validated against the reservation; reservations are not
reduced to actual usage, so the trial can end before five searches.

The accounting key is fixed to the approved trial, not to the deployment or
release fingerprint. Counters do not expire and redeploys do not reset them.
Changed policies, missing/corrupt state, duplicate attempts and unavailable Redis
all fail closed. Provisioning is an explicit one-time operator action; runtime
reservations never create missing state. Do not call `provision()` automatically
at startup or on deployments, clear the trial key, or enable eviction. The real
trial key was provisioned once on November 4, 2026 with zero initial usage.

Verified against the actual preview-connected Redis instance using separate test
namespaces: 12 simultaneous search reservations admitted exactly 5 and blocked 7;
token, dollar and call-count ceilings, duplicate attempts and missing-state denial
all passed. The verification used no model calls. Test counters are distinct from
real trial accounting. A temporary protected verification function was used for
this check and removed from the current preview afterward.

The v2 verification also exercised exact summary bindings and 12 concurrent
ticket consumers: exactly one succeeded, eleven replays were blocked. Tickets
are random, single-use, and bound to the release, normalized query and exact
ordered top ten IDs. Only a token hash and opaque binding are kept in the same
trial hash; no raw query or paper IDs are stored. Search returns `search_token`;
the live answer endpoint requires it. A mismatched binding does not consume it,
but a correct consumption is final even if answer generation fails. Issuance
failure preserves papers and sets `summary_available: false` with
`summary_unavailable_reason: "authorization_unavailable"`.

The real ledger read on November 4, 2026 showed 5/5 searches, 96,290/100,000
reserved tokens, 9/20 calls and $0.0875589/$0.50 reserved estimated cost. Thus
the original trial is exhausted; another live test requires explicit approval
for a separately bounded trial. Verification did not reserve real-trial
usage or call a model. A deployment never replenishes this budget.

The user subsequently approved **a separate second trial: 2 searches, 200,000
reserved tokens, $0.50 estimated model cost and 12 model attempts**, stopping at
the first ceiling. `approved_trial()` maps `protected-trial-v2` to the fixed key
`arxiv:trial:arxiv-e2e-2026-11-04-v2` and those exact limits. It requires the
Decision 47/48 release and Vercel Preview. The original key/policy/counters are
unchanged; switching deployments does not allocate another ledger.

The new key was explicitly provisioned once with all counters zero. Separate
Redis verification namespaces confirmed two admissions out of twelve concurrent
search reservations, the 200,000-token ceiling, the twelve-call ceiling, and
single-use answer tickets. The operation compared the original counters before
and after and confirmed no change. Verification made zero model calls and used
neither real-trial search. Provisioning is not part of application startup.
The Preview-only activation setting is now `protected-trial-v2`; future preview
releases must preserve this same ledger, not choose another trial ID.

The manifest pins `vector_storage` separately from embedding identity. The selected
storage is float16 at all 3,072 dimensions; float32 remains supported for explicit
control releases (older manifests without the storage field mean float32).
Queries and score accumulation stay float32. Scoring converts at most 256 paper
rows at a time (about 3 MiB), without expanding the whole matrix or renormalizing
the rounded paper vectors. Load-time norm validation uses a 0.0005 tolerance for
float16 rounding and 0.00001 for float32.

The saved [dev compression check](../data/results/embedding-compression/report.md)
reports a -0.0005 Stage 1 nDCG@10 difference for float16 and identical top-50 sets
on 98/100 dev queries. That supports the storage choice, but is not a fresh Stage 2
evaluation or proof that reranked results are identical. Dimensions are not
truncated and int8 is not enabled. The storage setting is included in the release
fingerprint, so the change invalidates prior adapter cache keys.

Promote deliberately: update the release specification after a tested dev choice,
run offline contract/parity tests, export to a **new** directory, validate a
Vercel preview, then promote that preview. Keep the prior release for rollback.
The exporter refuses to overwrite an existing directory.

## Building an isolated release

Use Python 3.13 and a separate build environment. Do not downgrade the shared
development environment. The build dependencies include the cache reader's
HTTP/dotenv imports. NumPy, PyStemmer and tiktoken are the direct runtime packages.

From the repository root in PowerShell:

```powershell
# Replace py with the full path to an installed Python 3.13 if necessary.
py -3.13 -m venv data\serving\build-env
data\serving\build-env\Scripts\python.exe -m pip install -r serving\build-requirements.txt
data\serving\build-env\Scripts\python.exe -m arxiv_search.serving.export `
  --output data\serving\release-001
```

`data/serving/` is already ignored by git. Exported data is a deployment artifact,
not a source-code commit. Missing or corrupt vector-cache blocks stop the build
without any model call. The export directory contains only:

```
public/          frontend assets (no scripts, mock data, or documentation)
api/index.py     WSGI function
arxiv_search/    selected runtime modules only, no evaluation code
artifacts/       corpus, vectors, packed postings, manifest (not public assets)
requirements.txt
vercel.json
.python-version
```

Test locally from the generated directory, using the isolated interpreter:

```powershell
Push-Location data\serving\release-001
..\build-env\Scripts\python.exe -m arxiv_search.serving.http
Pop-Location
```

The API listens on `127.0.0.1:8000`. Metadata works; live searches and summaries
remain explicitly disabled. Same-origin production needs no CORS. Localhost
HTTP origins are allowlisted for API testing; the frontend's production CSP
still requires a same-origin API or an explicitly configured development policy.
`Retry-After` is exposed to allowlisted cross-origin clients.
On Vercel, the exact HTTPS origin provided by the platform's `VERCEL_URL` is
also allowed, so browser POSTs work on protected deployment previews.
Unrelated `*.vercel.app` origins and client-supplied Host headers are not trusted.

## Free Vercel path

The generated directory is a self-contained Vercel project using the explicit
`framework: null` ("Other") preset, with static assets in
`public/` and `/api/*` rewritten to one Python WSGI function. Deploy **that
directory**, not the repository root or the current static-only `web/` project.
It deliberately omits `.env`, research data, model caches, Torch and
sentence-transformers. Its Python package pins have Linux CPython 3.13 wheels.

Before deploying, inspect the generated files. If using the Vercel CLI, create
or link a **preview project** from inside the generated directory and deploy a
preview there. No production/domain switch is made by this exporter. Promoting
the new layout replaces the existing static-only deployment workflow; the old
`web/` ignore command must not remain the serving deployment's trigger.

Current documented Hobby limits with Fluid compute: 500 MB uncompressed Python
function bundle, 2 GB memory and up to 300 seconds per invocation. This bundle
sets a more conservative 120-second function ceiling. Hobby also has monthly
CPU, memory-time and transfer quotas and is for personal/non-commercial use.
Free hosting is not unlimited availability.

**Observed deployment constraints take precedence over the advertised limit.**
The first upload failed at 100 MB per file. After sharding, the file-based Python
builder rejected a 231.84 MB bundle against its enforced **225 MB** maximum.
Losslessly compressing the corpus resolved this; the successful Vercel build
reports a **181.33 MB function**. Do not rely on the 500 MB documentation alone.
Automatic Python framework detection also failed to match the file-based function;
the exporter now explicitly selects "Other".

The first successful upload directory was about 174 MB before installed dependencies.
On the initial model-disabled protected preview, authenticated checks verified:

- frontend and `/api/meta`: HTTP 200, with the expected 23,304-paper release;
- `/api/search` and `/api/summary`: HTTP 503 with explicit `budget_exhausted`
  responses, proving paid calls remain disabled;
- corpus, vector shard, manifest, runtime source, requirements and `.env` paths:
  HTTP 404 even with preview authentication bypassed;
- one warm metadata request: approximately 0.17 seconds end to end;
- original `arxiv.agarwal-labs.com`: frontend still HTTP 200, API still HTTP 404.

These are routing and artifact-load checks, not live retrieval/model performance
measurements. The first successful metadata request initialized the real artifacts,
but a controlled hosted cold-start benchmark and full retrieval/concurrency memory
test remain pending.

The guarded model-enabled preview has a **187.64 MB optimized function**. Its
metadata request successfully initialized the pinned adapters, offline tokenizers,
release artifacts, OpenAI key configuration and shared trial ledger without
calling a model. The one-time operator deployment was deleted; its provisioning
endpoint returns 404 on the clean preview. No automatic live search was run:
the user's first question is reserved for the first model-enabled end-to-end test.
Browser validation with fixture data verified 10 top results, 10 more results,
the explicit summary-unavailable notice and zero summary requests.

The research-workspace redesign reuses the same checksummed runtime and corpus
release, updating public assets only. Its theme script is included in the export
allowlist. The protected deployment verified HTTP 200 for both the new script and
metadata, retaining the same release fingerprint and trial limits. UI checks used
fixture responses, not live model calls. No conversational memory is implemented.

Earlier local measurements on the full 23,304-paper corpus with prebuilt BM25,
before adding sharding and lossless corpus compression:

- about 204 MB upload files before dependencies (143 MB of paper vectors);
- about 264 MB including the downloaded Linux wheels' uncompressed contents;
- about 503 MB peak process working set on Windows;
- approximately 1.2 seconds to check/load artifacts and 0.6 seconds to load BM25;
- approximately 0.25 seconds for one retrieval-only smoke call.

This trades additional float16-to-float32 conversion CPU for substantially smaller
storage and memory. The previous float32 smoke was about 0.02 seconds, with a
408 MB estimated bundle and 634 MB peak working set. Chunked scores differed from
a full-matrix float32 calculation on the same float16 data by at most 3.9e-7
in the full-corpus smoke; floating-point batching need not be bit-identical.

These are **local feasibility measurements, not Vercel measurements or live
search latency**. The smoke used an existing document vector, not a network query
embedding. Platform wrapper/bytecode overhead is not included in the local size
estimate. The preview has now verified the actual bundle and rewrite behavior.
Hosted retrieval memory, controlled cold starts, concurrency and function timeout
still need validation before production.

Sources checked November 4, 2026:

- [Function limits](https://vercel.com/docs/functions/limitations)
- [Hobby allowances and fair use](https://vercel.com/docs/plans/hobby)
- [Python runtime and bundling](https://vercel.com/docs/functions/runtimes/python)
- [File-based Python handlers](https://vercel.com/docs/functions/runtimes/python/api-directory)

## Protected-trial behavior and remaining production gates

1. Embedding and two-pass score transports are implemented in `provider.py`.
   The score prompt, schema, model, full abstracts and all authors match the
   research payload. Serving uses the query string instead of a development
   query ID in the existing SHA-256 presentation recipe. Both passes see
   identical input. This is not a fresh quality evaluation.
   The v2 refinement and answer adapters are pinned as described above; v1
   continues to return `meta.summary_available: false`.
2. The Redis guard is wired into every provider attempt, and the approved trial
   is provisioned. Separate daily production budgets and
   per-client/global rate limits remain future work; the current guard enforces
   the bounded protected trial. Fail closed if the store is unavailable. Do not
   use process-local counters, `/tmp`, or bundled SQLite for global limits.
3. Keep production and experiment usage allocations separate, accounting for any
   provider account-wide quota. A provider free allowance is not a guarantee of
   zero charges.
4. The protected trial has explicit approval within the limits above; wider usage
   needs separate approval. Keep credentials server-side only.
5. Add durable versioned caching. Both scoring passes already run concurrently
   within each stage. Current
   embedding and reranking transport timeouts are 10 and 35 seconds per attempt.
   The function timeout is 120 seconds and the browser allows 150 seconds.
   Reranker budget/rate/provider failures retain retrieval order;
   summary failure must not discard search results.
6. Validate a preview, then explicitly switch the live deployment. No hosting
   account, billing setting or production domain is modified by this implementation.

## Offline validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_serving.py `
  tests\test_serving_export.py tests\test_serving_budget.py tests\test_serving_provider.py tests\test_bm25.py tests\test_rank_score.py `
  tests\test_rerank.py -q
```

The tests cover request validation, CORS, error sanitization, `Retry-After`, result
limits, author truncation/full abstracts, exact retrieval-helper parity, reranking
fallback, citation bounds/abstention, model compatibility, artifact corruption,
runtime drift, isolated packaging, preview-only activation, reservation-before-network,
no retries, score prompt parity, offline tokenization and a complete mocked
embedding/retrieval/two-pass-reranking HTTP request.
