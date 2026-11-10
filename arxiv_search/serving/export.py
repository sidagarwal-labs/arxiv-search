"""Build an isolated Vercel upload directory using existing cached vectors only."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
import tiktoken

from arxiv_search import config
from arxiv_search.evaluate.openai_full import BATCH_SIZE, CACHE, read_cache
from arxiv_search.search.text import paper_text
from arxiv_search.serving.lexical import write_index
from arxiv_search.serving.release import Release, sha256_file

RUNTIME_FILES = (
    "__init__.py", "config.py", "answer.py", "search/__init__.py", "search/bm25.py",
    "search/text.py", "search/hybrid.py", "search/rank_score.py",
    "search/score_fusion.py", "search/rerank.py", "serving/__init__.py",
    "serving/release.py", "serving/service.py", "serving/http.py", "serving/lexical.py",
    "serving/budget.py", "serving/provider.py", "serving/tracing.py",
)
PAPER_RUNTIME_FILES = (
    "paper_text.py", "paper_chat.py", "serving/paper_state.py", "serving/paper_content.py",
    "serving/paper_service.py", "serving/paper_loader.py",
    "serving/paper_preview.py", "serving/paper_live.py",
)


def export_release(output: Path, specification: Path, corpus_path: Path,
                   cache: Path, *, requirements_path: Path | None = None,
                   include_paper: bool = False, prepare_preview: bool = False,
                   include_tracing: bool = False) -> dict:
    if prepare_preview and not include_paper:
        raise ValueError("Preparation Preview requires the explicitly included paper runtime")
    if output.exists():
        raise FileExistsError("Output must be a new directory; existing releases are never overwritten")
    requirements_path = requirements_path or (
        config.PROJECT_ROOT / "serving" / (
            "runtime-paper-requirements.txt" if include_paper else "runtime-requirements.txt"
        )
    )
    requirements_text = requirements_path.read_text()
    if include_tracing:
        requirements_text = requirements_text.rstrip() + "\n" + (
            config.PROJECT_ROOT / "serving" / "runtime-tracing-requirements.txt"
        ).read_text()
    dependencies = dict(
        line.strip().split("==") for line in requirements_text.splitlines()
        if line.strip()
    )
    if include_paper and not {"beautifulsoup4", "pypdf", "tiktoken"} <= dependencies.keys():
        raise ValueError("Paper packaging requires explicitly pinned parser/tokenizer dependencies")
    for package, pinned in dependencies.items():
        if version(package) != pinned:
            raise ValueError(
                f"Export requires {package}=={pinned}; build in an isolated pinned environment"
            )
    spec = json.loads(specification.read_text(encoding="utf-8"))
    storage = spec.get("vector_storage", "float32")
    if storage not in ("float16", "float32"):
        raise ValueError("Vector storage must be float16 or float32")
    if spec["embedding"] != {
        "provider": "openai", "model": "text-embedding-3-large", "dimensions": 3072,
        "text_recipe": "title-abstract-v1",
    }:
        raise ValueError("This cache exporter only supports the OpenAI-large 3072 text recipe")
    corpus_bytes = corpus_path.read_bytes()
    papers = [json.loads(line) for line in corpus_bytes.splitlines() if line]
    ids = [p["arxiv_id"] for p in papers]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Corpus must contain unique papers")
    # Preflight every cache block before writing anything; never call embed() or repair caches.
    texts = [paper_text(p) for p in papers]
    for start in range(0, len(texts), BATCH_SIZE):
        if read_cache(texts[start:start + BATCH_SIZE], cache) is None:
            raise ValueError(f"Missing cached vectors at corpus offset {start}; no API calls made")
    output.mkdir(parents=True)
    artifacts = output / "artifacts"
    artifacts.mkdir()
    corpus_file = "corpus.jsonl.gz"
    (artifacts / corpus_file).write_bytes(gzip.compress(corpus_bytes, mtime=0))
    shard_rows = 4096
    shards = []
    for offset in range(0, len(papers), shard_rows):
        rows = min(shard_rows, len(papers) - offset)
        name = f"vectors-{len(shards):03d}.npy"
        vectors = np.lib.format.open_memmap(
            artifacts / name, mode="w+", dtype=np.dtype(storage),
            shape=(rows, spec["embedding"]["dimensions"]),
        )
        for start in range(offset, offset + rows, BATCH_SIZE):
            block = read_cache(texts[start:start + BATCH_SIZE], cache)
            if block is None:
                raise ValueError("Cache changed during export; incomplete output must not be deployed")
            vectors[start - offset:start - offset + len(block)] = block
        vectors.flush()
        del vectors
        shards.append(name)
    write_index(papers, spec["retrieval"], artifacts)
    tokenizers = {}
    for name in ("cl100k_base", "o200k_base"):
        encoding = tiktoken.get_encoding(name)
        tokenizers[name] = {
            "pattern": encoding._pat_str,
            "ranks": [[base64.b64encode(token).decode("ascii"), rank]
                      for token, rank in encoding._mergeable_ranks.items()],
        }
    tokenizer_file = "tokenizers.json"
    (artifacts / tokenizer_file).write_text(
        json.dumps(tokenizers, separators=(",", ":")), encoding="utf-8",
    )
    months = sorted({p["submitted_month"] for p in papers})
    counts = {cat: sum(p["primary_category"] == cat for p in papers)
              for cat in sorted({p["primary_category"] for p in papers})}
    spec.update({
        "papers": len(papers), "categories": list(counts),
        "corpus_file": corpus_file,
        "vector_shards": shards,
        "tokenizer_file": tokenizer_file,
        "from_month": months[0], "to_month": months[-1], "fields": "title+abstract",
        "corpus_note": "Fixed primary-category snapshot; cs.CL and cs.LG are capped samples. "
                       "No full text or human relevance validation. Category counts: "
                       + json.dumps(counts, sort_keys=True),
        "sha256": {name: sha256_file(artifacts / name)
                   for name in (corpus_file, "bm25.npz", "terms.json", tokenizer_file, *shards)},
    })
    runtime_files = RUNTIME_FILES + (PAPER_RUNTIME_FILES if include_paper else ())
    for relative in runtime_files:
        source = config.PROJECT_ROOT / "arxiv_search" / relative
        target = output / "arxiv_search" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    spec["runtime_sha256"] = {
        relative: sha256_file(output / "arxiv_search" / relative) for relative in runtime_files
    }
    spec["dependencies_sha256"] = hashlib.sha256(requirements_text.encode("utf-8")).hexdigest()
    spec["runtime_dependencies"] = dependencies
    spec["source_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=config.PROJECT_ROOT, text=True,
    ).strip()
    (artifacts / "manifest.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    release = Release.load(artifacts)
    web = config.PROJECT_ROOT / "web"
    public = output / "public"
    public.mkdir()
    for name in ("index.html", "styles.css", "theme.js", "app.js", "portfolio.js", "paper-chat.js", "paper-api.js", "paper-reader.js", "api.js", "config.js", "favicon.svg",
                 "apple-touch-icon.png", "og-image.png", "robots.txt", "sitemap.xml"):
        shutil.copyfile(web / name, public / name)
    if prepare_preview:
        config_path = public / "config.js"
        text = config_path.read_text(encoding="utf-8")
        for field in ("PAPER_API_ENABLED", "PAPER_PREPARE_ONLY"):
            pattern = rf"\b{field}: (?:true|false)\b"
            text, replacements = re.subn(pattern, f"{field}: true", text)
            if replacements != 1:
                raise ValueError(f"Expected one boolean {field} configuration")
        config_path.write_text(text, encoding="utf-8")
    api = output / "api"
    api.mkdir()
    (api / "index.py").write_text(
        ("from arxiv_search.serving.paper_preview import create_application\n"
         "app = create_application()\n" if prepare_preview else
         "from arxiv_search.serving.http import app\n"), encoding="utf-8",
    )
    (output / "requirements.txt").write_bytes(requirements_text.encode("utf-8"))
    settings = json.loads((web / "vercel.json").read_text(encoding="utf-8"))
    settings.pop("ignoreCommand", None)
    settings.update({
        "framework": None,
        "buildCommand": "", "outputDirectory": "public",
        "functions": {"api/index.py": {
            "maxDuration": 120, "includeFiles": "{artifacts/**,arxiv_search/**}",
        }},
        "rewrites": [{"source": "/api/:path*", "destination": "/api/index"}],
    })
    (output / "vercel.json").write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    (output / ".python-version").write_text("3.13\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
    return {"release": release.fingerprint, "papers": len(papers),
            "upload_bytes_before_dependencies": size, "output": str(output),
            "paid_calls_enabled": False, "paper_runtime_packaged": include_paper,
            "paper_chat_enabled": False, "preparation_preview": prepare_preview}


def require_clean_source() -> None:
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        cwd=config.PROJECT_ROOT, text=True,
    )
    if status.strip():
        raise ValueError("Commit all source changes before exporting a deployment release")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--spec", type=Path,
                        default=config.PROJECT_ROOT / "serving" / "release-v1.json")
    parser.add_argument("--include-paper", action="store_true",
                        help="Package disabled paper adapters; does not activate endpoints or spending")
    parser.add_argument("--prepare-preview", action="store_true",
                        help="Enable only preparation; force search and paper model calls disabled")
    parser.add_argument("--include-tracing", action="store_true",
                        help="Include the pinned optional tracing dependencies")
    args = parser.parse_args()
    require_clean_source()
    print(json.dumps(export_release(
        args.output.resolve(), args.spec, config.PROCESSED_DIR / "corpus.jsonl", CACHE,
        include_paper=args.include_paper, prepare_preview=args.prepare_preview,
        include_tracing=args.include_tracing,
    ), indent=2))


if __name__ == "__main__":
    main()
