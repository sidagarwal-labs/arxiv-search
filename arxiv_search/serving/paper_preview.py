"""Preparation-only protected Preview. No session or model admission is possible."""

import os
from pathlib import Path
from threading import Lock

from arxiv_search.serving.budget import RedisREST
from arxiv_search.serving.paper_content import RedisContent
from arxiv_search.serving.paper_loader import ArxivTransport, PaperLoader
from arxiv_search.serving.paper_service import PaperService
from arxiv_search.serving.paper_state import Admission, PaperPolicy, RedisMetadata
from arxiv_search.serving.service import APIError

# Test infrastructure limits only. No paid paper trial or search budget is admitted.
PREVIEW_NAMESPACE = "paper:prepare-preview-20261105-v1"
PREVIEW_POLICY = PaperPolicy("prepare-preview-20261105-v1", 20, 1, 1, 1, 1)


class NoPaperProvider:
    def post(self, path, payload, *, timeout):
        raise APIError("budget_exhausted", "Paper models are disabled in this Preview.", 503)


class PreparationPreview:
    def __init__(self, release_factory):
        self.release_factory = release_factory
        self._service = None
        self._lock = Lock()

    def prepare(self, body: dict) -> dict:
        if os.environ.get("VERCEL_ENV") != "preview":
            raise APIError("budget_exhausted", "Preparation is restricted to protected Preview.", 503)
        with self._lock:
            if self._service is None:
                # Import only in an explicitly preparation-enabled package.
                from arxiv_search.serving.provider import TokenCounter
                release = self.release_factory().release
                signing_key = os.environ.get("ARXIV_PAPER_SIGNING_KEY", "")
                if len(signing_key) != 64:
                    raise APIError("upstream_unavailable", "Paper signing is not configured.", 503)
                try:
                    key = bytes.fromhex(signing_key)
                except ValueError:
                    raise APIError("upstream_unavailable", "Paper signing is invalid.", 503) from None
                redis = RedisREST(
                    os.environ.get("KV_REST_API_URL", ""),
                    os.environ.get("KV_REST_API_TOKEN", ""), max_response_bytes=12_000_100,
                )
                metadata = RedisMetadata(redis, PREVIEW_NAMESPACE)
                metadata.read()  # Read-only: never provision/reset missing infrastructure.
                name = release.manifest["tokenizer_file"]
                counter = TokenCounter(release.directory / name, release.manifest["sha256"][name])
                loader = PaperLoader(
                    {p["arxiv_id"]: p for p in release.papers}, counter.count_paper,
                    ArxivTransport(), timeout=20,
                )
                self._service = PaperService(
                    admission=Admission(metadata, PREVIEW_POLICY),
                    content=RedisContent(redis, PREVIEW_NAMESPACE), loader=loader.load,
                    transport=NoPaperProvider(), count_tokens=counter.count_paper, signing_key=key,
                )
        return self._service.prepare(body)

    def open(self, body: dict) -> dict:
        raise APIError("budget_exhausted",
                       "Preparation-only Preview: AI overview and conversation are disabled. "
                       "No session or model usage was admitted.", 503)

    def chat(self, body: dict) -> dict:
        return self.open(body)


def create_application():
    from arxiv_search.serving.http import Application
    from arxiv_search.serving.release import Release
    from arxiv_search.serving.service import DisabledEmbedder, SearchService

    def factory():
        # Ignore paid-search environment flags in this separate preparation-only package.
        directory = Path(__file__).resolve().parents[2] / "artifacts"
        release = Release.load(directory)
        return SearchService(release, DisabledEmbedder(release.embedding))

    application = Application(factory)
    application.paper_service = PreparationPreview(application.service)
    return application
