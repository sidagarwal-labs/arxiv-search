"""Central place for every tunable decision in the pipeline.

If a number affects what ends up in the index, it lives here so that it is
visible, versioned in git, and easy to cite in the project write-up.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # arxiv_search/config.py -> project folder
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # untouched API responses (immutable)
PROCESSED_DIR = DATA_DIR / "processed"  # cleaned corpus used by every later stage
EXPERIMENTS_DIR = DATA_DIR / "experiments"  # outputs of the scripts in experiments/

# --- Source: arXiv OAI-PMH ------------------------------------------------
OAI_BASE_URL = "https://oaipmh.arxiv.org/oai"
METADATA_PREFIX = "arXiv"  # arXiv-specific format: has <created>, <categories>, split authors
REQUEST_DELAY_SECONDS = 3  # arXiv asks for no more than 1 request every 3 seconds
USER_AGENT = "arxiv-search-dsba6188/0.1 (student course project)"

# --- Corpus selection (Decision 8) ----------------------------------------
CATEGORIES = ("cs.IR", "cs.CL", "cs.LG")  # kept if a paper's PRIMARY category is one of these
WINDOW_DAYS = 365  # keep papers first submitted (v1, month from arXiv ID) within this window
MAX_PER_CATEGORY = 10_000  # stratified cap so cs.LG doesn't drown out cs.IR
MIN_ABSTRACT_WORDS = 20  # drops stubs like "This paper has been withdrawn."
RANDOM_SEED = 6188  # fixed seed -> the same harvest always yields the same corpus

# --- LLM roles (Decision 20, writer changed in Decision 24) -----------------
# One model per role, sized to the reasoning the task needs. Gemini Flash's free tier
# allows only 20 calls/day per model, so the query writer is Gemma (much larger free
# quota). The judge choice is revisited when we build it (writer == judge risks self-preference).
QUERY_WRITER_MODEL = "gemma-4-31b-it"
JUDGE_MODEL = "gemma-4-31b-it"
RAG_MODEL_CANDIDATES = ("gemini-3.5-flash-lite", "gemini-3.5-flash")
RERANKER_MODEL_CANDIDATES = ("gemini-3.5-flash-lite", "gemini-3.5-flash")
HOSTED_EMBEDDING_MODEL = "gemini-embedding-2"
HOSTED_EMBEDDING_DIM = 768  # reduced from the default 3,072 so production vectors fit the free DB tier

# --- LLM calls on the free tier (see llm.py) -----------------------------
LLM_SECONDS_BETWEEN_CALLS = 6  # at most 10 requests per minute
LLM_MAX_RETRIES = 6  # retries on 503 (busy) / 429 (too fast), waiting 10 s, 20 s, 40 s, ...

# --- Evaluation query set (Decisions 22-23) ------------------------------
EVAL_DIR = DATA_DIR / "eval"
EVAL_QUERIES_PER_TYPE = 100  # 4 types -> 400 queries; keyword/question alternate specific/broad
EVAL_PAPERS_PER_CALL = 4  # one paper per query type in each call -> 100 calls total
EVAL_MAX_CALLS_PER_RUN = 150  # safety cap: 100 needed + room for retries of failed queries

# --- Evaluation metrics (Decision 21) ------------------------------------
RECALL_KS = (1, 5, 10, 20)  # 20 = the candidate pool a reranker / RAG would receive
MRR_CUTOFF = 10  # right paper at rank 11 or worse scores 0
NDCG_K = 10  # graded relevance 0/1/2, linear gain, unjudged papers count as 0
BOOTSTRAP_SAMPLES = 1_000  # resamples for 95% confidence intervals
