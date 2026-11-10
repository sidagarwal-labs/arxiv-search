from arxiv_search.serving.http import Application
from arxiv_search.serving.service import SearchService
from tests.test_serving import FakeEmbedder, FakeReranker, release, release_dir, request  # noqa: F401


class Transport:
    warmed = 0

    def warm(self):
        self.warmed += 1


def test_warm_loads_index_and_transport_once(release):
    embedder = FakeEmbedder(release)
    embedder.provider = type("Provider", (), {"transport": Transport()})()
    built = []

    def factory():
        built.append(SearchService(release, embedder, FakeReranker()))
        return built[-1]

    app = Application(factory)
    app.warm()
    service = built[0]
    retriever = service._retriever
    assert retriever is not None and embedder.provider.transport.warmed == 1
    response = request(app, "POST", "/api/search", {"query": "retrieval", "k": 3})
    assert response["status"] == 200 and len(response["body"]["results"]) == 3
    assert len(built) == 1 and service._retriever is retriever


def test_warm_failure_falls_back_to_lazy_loading(release):
    calls = []

    def factory():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("cold start failed")
        return SearchService(release, FakeEmbedder(release))

    app = Application(factory)
    app.warm()
    response = request(app, "GET", "/api/meta")
    assert response["status"] == 200 and response["body"]["papers"] > 0 and len(calls) == 2
