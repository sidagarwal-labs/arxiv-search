"""Step 1 (download): fetch raw arXiv metadata over OAI-PMH.

How OAI-PMH works (the 30-second version)
-----------------------------------------
1. We send `verb=ListRecords` with a `set` (a category such as `cs:cs:IR`),
   a `metadataPrefix` (the XML format), and a `from` date.
2. arXiv returns one page of records plus a `resumptionToken`.
3. We send the token back to get the next page, and repeat until the token is
   empty. That empty token means "you have everything".

Design choices
--------------
* Each page is saved as untouched XML under data/raw/<harvest_date>/<category>/.
  Parsing happens later (parse.py), so if we change how we parse, we never
  have to re-download.
* A small state.json records the next resumptionToken, so an interrupted
  download resumes where it stopped instead of starting over.
* `from` filters on the record's *datestamp* (last modification), not on the
  submission date. It is only a coarse pre-filter; clean.py applies the real
  "submitted in the last 12 months" rule using the month in the arXiv ID.

Usage:
    python -m arxiv_search.ingest.download
    python -m arxiv_search.ingest.download --categories cs.IR --days 30   # quick test
"""

from __future__ import annotations

import argparse
import json
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import requests

from arxiv_search import config

OAI_NS = {"oai": "http://www.openarchives.org/OAI/2.0/"}
MAX_RETRIES = 5


def category_to_set_spec(category: str) -> str:
    """'cs.IR' -> 'cs:cs:IR' (arXiv's OAI-PMH set naming: group:archive:category)."""
    archive, subject = category.split(".")
    return f"{archive}:{archive}:{subject}"


def fetch_page(session: requests.Session, params: dict) -> str:
    """GET one OAI-PMH page, honoring arXiv's flow control.

    A 503 with a Retry-After header is arXiv's polite way of saying "slow down";
    we wait the requested time. Other transient errors use exponential backoff.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(config.OAI_BASE_URL, params=params, timeout=120)
        except requests.RequestException as exc:
            wait = 2**attempt * config.REQUEST_DELAY_SECONDS
            print(f"  network error ({exc}); retry {attempt}/{MAX_RETRIES} in {wait}s")
            time.sleep(wait)
            continue

        if response.status_code == 200:
            return response.text
        if response.status_code == 503:
            wait = int(response.headers.get("Retry-After", 30))
            print(f"  503 from arXiv; waiting {wait}s as requested")
            time.sleep(wait)
            continue
        response.raise_for_status()

    raise RuntimeError(f"Giving up after {MAX_RETRIES} attempts: {params}")


def parse_page_control(xml_text: str) -> tuple[str | None, str | None]:
    """Return (resumption_token, oai_error_code) from a page.

    The token is None (or empty) on the last page. `noRecordsMatch` is a normal
    OAI-PMH error meaning the set had nothing in the date range.
    """
    root = ET.fromstring(xml_text)
    error = root.find("oai:error", OAI_NS)
    if error is not None:
        return None, error.get("code")
    token_el = root.find(".//oai:resumptionToken", OAI_NS)
    token = token_el.text.strip() if token_el is not None and token_el.text else None
    return token, None


def download_category(
    category: str, from_date: str, out_dir: Path, session: requests.Session
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / "state.json"
    state = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else {"next_page": 1, "resumption_token": None, "done": False}
    )
    if state["done"]:
        print(f"[{category}] already complete, skipping")
        return

    while True:
        if state["resumption_token"]:
            # Per the OAI-PMH spec, a resumption request carries ONLY the token.
            params = {"verb": "ListRecords", "resumptionToken": state["resumption_token"]}
        else:
            params = {
                "verb": "ListRecords",
                "set": category_to_set_spec(category),
                "metadataPrefix": config.METADATA_PREFIX,
                "from": from_date,
            }

        xml_text = fetch_page(session, params)
        token, error_code = parse_page_control(xml_text)
        if error_code == "noRecordsMatch":
            print(f"[{category}] no records in range")
            state.update(done=True, resumption_token=None)
            state_path.write_text(json.dumps(state, indent=2))
            return
        if error_code:
            raise RuntimeError(f"[{category}] OAI-PMH error: {error_code}")

        page_path = out_dir / f"page_{state['next_page']:04d}.xml"
        page_path.write_text(xml_text, encoding="utf-8")
        print(f"[{category}] saved {page_path.name}")

        state["next_page"] += 1
        state["resumption_token"] = token
        state["done"] = not token
        state_path.write_text(json.dumps(state, indent=2))

        if state["done"]:
            print(f"[{category}] complete ({state['next_page'] - 1} pages)")
            return
        time.sleep(config.REQUEST_DELAY_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--categories", nargs="+", default=list(config.CATEGORIES))
    parser.add_argument("--days", type=int, default=config.WINDOW_DAYS)
    parser.add_argument(
        "--harvest-date",
        default=date.today().isoformat(),
        help="Folder name for this snapshot; reuse it to resume an interrupted run.",
    )
    args = parser.parse_args()

    from_date = (date.fromisoformat(args.harvest_date) - timedelta(days=args.days)).isoformat()
    snapshot_dir = config.RAW_DIR / args.harvest_date
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # The manifest is the provenance record: what we asked for, from where, and when.
    manifest = {
        "endpoint": config.OAI_BASE_URL,
        "metadata_prefix": config.METADATA_PREFIX,
        "categories": args.categories,
        "from_date": from_date,
        "harvest_date": args.harvest_date,
        "window_days": args.days,
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    for category in args.categories:
        download_category(category, from_date, snapshot_dir / category, session)
        time.sleep(config.REQUEST_DELAY_SECONDS)

    print(f"Done. Raw snapshot: {snapshot_dir}")


if __name__ == "__main__":
    main()
