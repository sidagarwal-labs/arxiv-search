"""Persist the previously explored24 finer rank-fusion settings, without API calls.

python -m arxiv_search.evaluate.fusion_refinement
"""

import json

from arxiv_search import config
from arxiv_search.evaluate import fusion_experiment as fusion, judge
from arxiv_search.search.hybrid import fuse

OUT = config.RESULTS_DIR / "refinement-dev"


def grid() -> dict:
    return {
        f"fusion-rrf+w={weight:g}+d=100+c={c}": {
            "semantic_weight": weight, "c": c, "depth": 100, "k": 100}
        for weight in (0.5, 0.55, 0.6, 0.65, 0.7, 0.75) for c in (10, 30, 60, 100)
    }


def main() -> None:
    papers, queries, split = judge.load_inputs()
    qids = sorted(split["dev"])
    if set(qids) & set(split["test"]):
        raise ValueError("Dev/test overlap")
    sources = {}
    for name in (fusion.LEXICAL, fusion.SEMANTIC):
        sources[name] = json.loads(
            (config.RESULTS_DIR / "dev" / f"{name}.run.json").read_text(encoding="utf-8"))
        fusion.validate_run(name, sources[name], qids, papers, exact_depth=100)
    configs = grid()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, options in configs.items():
        run = {q: fuse(sources[fusion.LEXICAL][q], sources[fusion.SEMANTIC][q], **options)
               for q in qids}
        fusion._write_json(OUT / f"{name}.run.json", run)
    fusion._write_json(OUT / "configs.json", configs)
    (OUT / "report.md").write_text(
        "# Finer rank-fusion grid\n\n"
        "24 previously explored settings, now all persisted for the unified scorecard. "
        "No API calls, label changes or baseline promotion. Score these saved rankings "
        "through the unified catalog using its shared snapshot; any missing judgments "
        "remain provisional. The pre-promotion review preserves its historical snapshot.\n",
        encoding="utf-8")
    print(f"Persisted {len(configs)} cached refinement runs; no API calls.")


if __name__ == "__main__":
    main()
