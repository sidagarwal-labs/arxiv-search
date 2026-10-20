"""Central place for every tunable decision in the pipeline.

If a number affects what ends up in the index, it lives here so that it is
visible, versioned in git, and easy to cite in the project write-up.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # untouched API responses (immutable)
PROCESSED_DIR = DATA_DIR / "processed"  # cleaned corpus used by every later stage

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
