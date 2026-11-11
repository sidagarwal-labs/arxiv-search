import json
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pytest

from arxiv_search.evaluate.openai_full import write_cache
from arxiv_search.search.text import paper_text
from arxiv_search.serving.export import export_release, require_clean_source
from arxiv_search.serving.release import Release
from arxiv_search.serving.service import LocalRetriever


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("status", ["", " M web/app.js\n", "?? arxiv_search/serving/http.py\n"])
def test_deployment_requires_committed_source(monkeypatch, status):
    monkeypatch.setattr("arxiv_search.serving.export.subprocess.check_output",
                        lambda *args, **kwargs: status)
    if status:
        with pytest.raises(ValueError, match="Commit all source"):
            require_clean_source()
    else:
        require_clean_source()


@pytest.fixture
def requirements(tmp_path):
    path = tmp_path / "requirements.txt"
    path.write_text("".join(f"{p}=={version(p)}\n" for p in ("numpy", "PyStemmer")))
    return path


def source(tmp_path):
    papers = [{
        "arxiv_id": f"2510.{i:05d}", "title": f"Retrieval paper {i}",
        "abstract": "A full abstract about retrieval.", "authors": ["An Author"],
        "primary_category": "cs.IR", "categories": ["cs.IR"], "submitted_month": "2025-10",
    } for i in range(3)]
    corpus = tmp_path / "source.jsonl"
    corpus.write_text("".join(json.dumps(p) + "\n" for p in papers), encoding="utf-8")
    vectors = np.zeros((3, 3072), dtype=np.float32)
    vectors[:, 0] = 1
    cache = tmp_path / "cache"
    write_cache([paper_text(p) for p in papers], vectors, cache)
    return corpus, cache


def test_export_is_isolated_self_contained_and_never_overwrites(tmp_path, requirements):
    corpus, cache = source(tmp_path)
    output = tmp_path / "bundle"
    result = export_release(output, ROOT / "serving" / "release-v1.json", corpus, cache,
                            requirements_path=requirements)
    assert result["papers"] == 3 and not result["paid_calls_enabled"]
    release = Release.load(output / "artifacts")
    assert release.vectors.dtype == np.float16
    assert release.vectors.shape == (3, 3072)
    assert release.manifest["vector_shards"] == ["vectors-000.npy"]
    assert release.manifest["corpus_file"] == "corpus.jsonl.gz"
    assert not (output / "artifacts" / "corpus.jsonl").exists()
    import gzip
    assert gzip.decompress((output / "artifacts" / "corpus.jsonl.gz").read_bytes()) == corpus.read_bytes()
    assert not (output / "artifacts" / "vectors.npy").exists()
    np.testing.assert_array_equal(release.vectors[:, 0], np.ones(3, dtype=np.float16))
    assert len(LocalRetriever(release).retrieve("retrieval", release.vectors[0], 3)) == 3
    assert (output / "api" / "index.py").is_file()
    assert (output / "public" / "index.html").is_file()
    assert (output / "public" / "theme.js").is_file()
    assert (output / "public" / "portfolio.js").is_file()
    assert (output / "public" / "paper-chat.js").is_file()
    assert (output / "public" / "paper-api.js").is_file()
    assert (output / "public" / "paper-reader.js").is_file()
    assert not (output / "public" / "paper-api.test.mjs").exists()
    settings = json.loads((output / "vercel.json").read_text())
    assert settings["buildCommand"] == ""
    assert settings["outputDirectory"] == "public"
    assert (output / "api" / "index.py").is_file()
    assert settings["rewrites"] == [{"source": "/api/:path*", "destination": "/api/index"}]
    headers = {h["key"].lower(): h["value"] for h in settings["headers"][0]["headers"]}
    assert "x-frame-options" not in headers
    assert "frame-ancestors 'self' https://agarwal-labs.com https://www.agarwal-labs.com" in headers["content-security-policy"]
    assert (output / "arxiv_search" / "answer.py").is_file()
    assert not (output / "arxiv_search" / "paper_chat.py").exists()
    assert not (output / ".env").exists()
    assert not (output / "arxiv_search" / "evaluate").exists()
    assert not (output / "public" / "scripts").exists()
    assert not (output / "public" / "mock").exists()
    assert not (output / "public" / "artifacts").exists()
    with pytest.raises(FileExistsError):
        export_release(output, ROOT / "serving" / "release-v1.json", corpus, cache)
    runtime = output / "arxiv_search" / "search" / "bm25.py"
    runtime.write_text("# changed after promotion\n")
    with pytest.raises(ValueError, match="Runtime code"):
        Release.load(output / "artifacts")


def test_missing_cache_fails_before_creating_output(tmp_path, requirements):
    corpus, _ = source(tmp_path)
    output = tmp_path / "bundle"
    with pytest.raises(ValueError, match="Missing cached vectors"):
        export_release(output, ROOT / "serving" / "release-v1.json", corpus, tmp_path / "missing",
                       requirements_path=requirements)
    assert not output.exists()


def test_paper_export_is_explicit_checksummed_and_still_disabled(tmp_path):
    corpus, cache = source(tmp_path)
    output = tmp_path / "paper-bundle"
    result = export_release(
        output, ROOT / "serving" / "release-v3.json", corpus, cache, include_paper=True,
    )
    assert result["paper_runtime_packaged"] is True
    assert result["paper_chat_enabled"] is False
    assert result["paid_calls_enabled"] is False
    release = Release.load(output / "artifacts")
    for path in ("paper_chat.py", "paper_text.py", "serving/paper_service.py",
                 "serving/paper_content.py", "serving/paper_state.py", "serving/paper_loader.py"):
        assert path in release.manifest["runtime_sha256"]
        assert (output / "arxiv_search" / path).is_file()
    assert release.manifest["runtime_dependencies"]["pypdf"] == version("pypdf")
    assert (output / "api" / "index.py").read_text() == "from arxiv_search.serving.http import app\n"


def test_tracing_export_pins_combined_dependencies(tmp_path, requirements, monkeypatch):
    tracing = dict(line.split("==") for line in
                   (ROOT / "serving" / "runtime-tracing-requirements.txt").read_text().splitlines()
                   if line.strip())
    monkeypatch.setattr("arxiv_search.serving.export.version",
                        lambda package: tracing[package] if package in tracing else version(package))
    monkeypatch.setattr("arxiv_search.serving.release.version",
                        lambda package: tracing[package] if package in tracing else version(package))
    corpus, cache = source(tmp_path)
    output = tmp_path / "traced-bundle"
    export_release(output, ROOT / "serving" / "release-v4.json", corpus, cache,
                   requirements_path=requirements, include_tracing=True)
    manifest = json.loads((output / "artifacts" / "manifest.json").read_text())
    assert manifest["runtime_dependencies"]["langsmith"] == tracing["langsmith"]
    assert "numpy==" in (output / "requirements.txt").read_text()
    from arxiv_search.serving.release import sha256_file
    assert manifest["dependencies_sha256"] == sha256_file(output / "requirements.txt")


def test_preparation_preview_export_forces_disabled_model_factory(tmp_path):
    corpus, cache = source(tmp_path)
    output = tmp_path / "prepare-bundle"
    result = export_release(
        output, ROOT / "serving" / "release-v3.json", corpus, cache,
        include_paper=True, prepare_preview=True,
    )
    assert result["preparation_preview"] is True
    assert result["paid_calls_enabled"] is result["paper_chat_enabled"] is False
    assert "create_application" in (output / "api" / "index.py").read_text()
    text = (output / "public" / "config.js").read_text()
    assert "PAPER_API_ENABLED: true" in text
    assert "PAPER_PREPARE_ONLY: true" in text


def test_paper_export_rejects_missing_parser_pins_before_writing(tmp_path, requirements):
    with pytest.raises(ValueError, match="pinned parser"):
        export_release(tmp_path / "bundle", ROOT / "serving" / "release-v3.json",
                       tmp_path / "unused", tmp_path / "unused",
                       requirements_path=requirements, include_paper=True)
    assert not (tmp_path / "bundle").exists()


def test_export_refuses_wrong_dependency_versions(tmp_path):
    requirements = tmp_path / "wrong.txt"
    requirements.write_text("numpy==0.0.0\n")
    with pytest.raises(ValueError, match="isolated pinned environment"):
        export_release(tmp_path / "bundle", ROOT / "serving" / "release-v1.json",
                       tmp_path / "unused", tmp_path / "unused", requirements_path=requirements)


def test_sharded_load_preserves_exact_row_order(tmp_path, requirements):
    corpus, cache = source(tmp_path)
    output = tmp_path / "bundle"
    export_release(output, ROOT / "serving" / "release-v1.json", corpus, cache,
                   requirements_path=requirements)
    artifacts = output / "artifacts"
    original = Release.load(artifacts).vectors.copy()
    original[1, 0] = 0
    original[1, 1] = 1
    from arxiv_search.serving.release import sha256_file
    manifest_path = artifacts / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    shards = ["part-0.npy", "part-1.npy"]
    for name, block in zip(shards, (original[:1], original[1:])):
        np.save(artifacts / name, block, allow_pickle=False)
        manifest["sha256"][name] = sha256_file(artifacts / name)
    manifest["vector_shards"] = shards
    manifest_path.write_text(json.dumps(manifest))
    loaded = Release.load(artifacts)
    np.testing.assert_array_equal(loaded.vectors, original)
    assert not loaded.vectors.flags.writeable
    manifest["vector_shards"].reverse()
    manifest_path.write_text(json.dumps(manifest))
    reordered = Release.load(artifacts)
    assert reordered.fingerprint != loaded.fingerprint
    np.testing.assert_array_equal(reordered.vectors, original[[1, 2, 0]])
    manifest["vector_shards"] = ["part-0.npy"]
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="dimensions"):
        Release.load(artifacts)
