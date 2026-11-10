import pytest

from arxiv_search.serving.paper_preview import PreparationPreview, NoPaperProvider
from arxiv_search.serving.service import APIError


@pytest.mark.parametrize("operation", ["open", "chat"])
def test_preparation_preview_cannot_create_sessions_or_reserve_calls(operation):
    def forbidden():
        raise AssertionError("Search/release factory must not run")

    preview = PreparationPreview(forbidden)
    with pytest.raises(APIError) as error:
        getattr(preview, operation)({})
    assert error.value.code == "budget_exhausted"
    assert "No session or model usage" in str(error.value)


def test_disabled_provider_never_has_a_network_transport():
    with pytest.raises(APIError) as error:
        NoPaperProvider().post("responses", {}, timeout=1)
    assert error.value.code == "budget_exhausted"


def test_prepare_preview_cannot_run_in_production(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    preview = PreparationPreview(lambda: None)
    with pytest.raises(APIError, match="restricted"):
        preview.prepare({})
