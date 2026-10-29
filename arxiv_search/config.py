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
RAG_MODEL_CANDIDATES = ("gemini-3.5-flash-lite", "gemini-3.5-flash")
RERANKER_MODEL_CANDIDATES = ("gemini-3.5-flash-lite", "gemini-3.5-flash")
HOSTED_EMBEDDING_MODEL = "gemini-embedding-2"
HOSTED_EMBEDDING_DIM = 768  # reduced from the default 3,072 so production vectors fit the free DB tier

# --- LLM calls on the free tier (see llm.py) -----------------------------
LLM_SECONDS_BETWEEN_CALLS = 6  # at most 10 requests per minute
LLM_MAX_RETRIES = 6  # retries on 503 (busy) / 429 (too fast), waiting 10 s, 20 s, 40 s, ...
LLM_REQUEST_TIMEOUT_SECONDS = 120

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

# --- Experiments (Decisions 26-27) ----------------------------------------
RESULTS_DIR = DATA_DIR / "results"  # rankings + per-query scores of every system run
RUN_DEPTH = 100  # papers kept per query: enough for Recall@20 and for a reranker / judge later
BASELINE_SYSTEM = "bm25-baseline"  # every other system is compared against this one

# --- Relevance judge (Decision 33) -----------------------------------------
# Pilot: both judges grade the same pairs; the user's blind grades decide which to keep.
JUDGES = {
    "gemma-31b": {"backend": "gemini", "model": "gemma-4-31b-it"},  # API; same model wrote the queries
    "qwen2.5-7b": {"backend": "ollama", "model": "qwen2.5:7b"},  # local; independent of the writer
}
JUDGMENTS_DIR = EVAL_DIR / "judgments"  # one cache file per judge: <judge>.jsonl
JUDGE_POOL_SYSTEMS = [  # papers in any of these systems' top JUDGE_POOL_DEPTH get graded
    "bm25+exact+stems+authors+title2x+k1=0.8,b=0.75",
    "dense-gte-small",
    "dense-bge-small",
    "hybrid-gte-small+rrf+w=0.5+c=10",
    "hybrid-bge-small+rrf+w=0.5+c=10",
]
JUDGE_POOL_DEPTH = 10  # = NDCG_K: the papers nDCG@10 looks at (~23 unique per query)
JUDGE_MAX_PAPERS_PER_CALL = 30  # one call per query; a bigger pool is split into calls
GEMMA_JUDGE_MAX_PAPERS_PER_CALL = 10  # smaller replies reduce missing/mistyped labels
JUDGE_PILOT_QUERIES_PER_TYPE = 3  # 12 pilot queries
JUDGE_PILOT_HUMAN_PAIRS_PER_TYPE = 25  # 100 pairs graded blind by a person
OLLAMA_URL = "http://localhost:11434"
OLLAMA_CONTEXT_TOKENS = 16_384  # Ollama's default window is too small for ~25 abstracts

# --- Local embedding models (Decisions 25, 31) ------------------------------
# All small (384 numbers per vector), selected as candidates for cheap query embedding
# on a server CPU or in the browser. Some models were trained with a fixed text in front of
# queries and papers; leaving it out makes them worse, so it's part of the model's settings.
EMBEDDINGS_DIR = DATA_DIR / "embeddings"  # one vector file per model (rebuildable, not in git)
EMBEDDING_MODELS = {
    "minilm": {  # the model from class; reads only the first 256 tokens (cuts off 68% of papers)
        "hf_name": "sentence-transformers/all-MiniLM-L6-v2",
        "query_prefix": "", "paper_prefix": "",
    },
    "bge-small": {
        "hf_name": "BAAI/bge-small-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ", "paper_prefix": "",
    },
    "e5-small": {
        "hf_name": "intfloat/e5-small-v2",
        "query_prefix": "query: ", "paper_prefix": "passage: ",
    },
    "gte-small": {
        "hf_name": "thenlper/gte-small",
        "query_prefix": "", "paper_prefix": "",
    },
}
EMBEDDING_BATCH_SIZE = 32
