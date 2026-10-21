from datetime import date

from arxiv_search import config
from arxiv_search.ingest.clean import clean_corpus, stratified_sample
from arxiv_search.ingest.download import category_to_set_spec, parse_page_control
from arxiv_search.ingest.parse import parse_page, submitted_month_from_id

LONG_ABSTRACT = " ".join(["word"] * 30)

PAGE = f"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header><identifier>oai:arXiv.org:2601.00001</identifier></header>
      <metadata>
        <arXiv xmlns="http://arxiv.org/OAI/arXiv/">
          <id>2601.00001</id>
          <created>2026-01-05</created>
          <authors>
            <author><keyname>Doe</keyname><forenames>Jane</forenames></author>
          </authors>
          <title>Dense   Retrieval
            for Science</title>
          <categories>cs.IR cs.CL</categories>
          <abstract>  {LONG_ABSTRACT}
          </abstract>
        </arXiv>
      </metadata>
    </record>
    <record>
      <header status="deleted"><identifier>oai:arXiv.org:2601.00002</identifier></header>
    </record>
    <resumptionToken cursor="0">abc123</resumptionToken>
  </ListRecords>
</OAI-PMH>"""


def make(arxiv_id, primary, submitted_month="2026-06", abstract=LONG_ABSTRACT, comments=None):
    return {
        "arxiv_id": arxiv_id,
        "primary_category": primary,
        "submitted_month": submitted_month,
        "abstract": abstract,
        "comments": comments,
    }


def test_set_spec():
    assert category_to_set_spec("cs.IR") == "cs:cs:IR"


def test_submitted_month_from_id():
    assert submitted_month_from_id("2308.09419") == "2023-08"
    assert submitted_month_from_id("cs/0101001") is None


def test_parse_page_extracts_fields_and_skips_deleted():
    records = list(parse_page(PAGE))
    assert len(records) == 1
    r = records[0]
    assert r["title"] == "Dense Retrieval for Science"  # whitespace collapsed
    assert r["primary_category"] == "cs.IR"
    assert r["categories"] == ["cs.IR", "cs.CL"]
    assert r["authors"] == ["Jane Doe"]
    assert r["url"] == "https://arxiv.org/abs/2601.00001"
    assert r["submitted_month"] == "2026-01"


def test_resumption_token_and_errors():
    assert parse_page_control(PAGE) == ("abc123", None)
    no_match = (
        '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">'
        '<error code="noRecordsMatch"/></OAI-PMH>'
    )
    assert parse_page_control(no_match) == (None, "noRecordsMatch")


def test_clean_corpus_filters():
    records = [
        make("1", "cs.IR"),
        make("1", "cs.IR"),  # duplicate from cross-list download
        make("2", "cs.CV"),  # wrong primary category
        make("3", "cs.CL", submitted_month="2023-08"),  # old paper, recently revised
        make("4", "cs.LG", abstract="too short"),  # stub
        make("5", "cs.LG", comments="This paper has been withdrawn"),
    ]
    corpus, stats = clean_corpus(records, harvest_date=date(2026, 10, 20))
    assert [r["arxiv_id"] for r in corpus] == ["1"]
    assert stats["stages"]["deduplicated"]["total"] == 5


def test_stratified_sample_caps_and_is_deterministic():
    records = [make(f"lg{i:03d}", "cs.LG") for i in range(50)] + [make("ir1", "cs.IR")]
    a = stratified_sample(records, cap=10, seed=config.RANDOM_SEED)
    b = stratified_sample(list(reversed(records)), cap=10, seed=config.RANDOM_SEED)
    assert a == b  # input order doesn't matter
    assert sum(r["primary_category"] == "cs.LG" for r in a) == 10
    assert sum(r["primary_category"] == "cs.IR" for r in a) == 1  # small category kept whole
