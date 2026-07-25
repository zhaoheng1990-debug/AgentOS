"""Verify locally cached external benchmark artifacts without Provider calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_collective_cognition.factorized_benchmarks.smoke import run_smoke


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scifact", type=Path, required=True)
    parser.add_argument("--ebm-nlp", type=Path, required=True)
    parser.add_argument("--qasper-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_smoke(
        scifact_archive=args.scifact,
        ebm_archive=args.ebm_nlp,
        qasper_fixture=args.qasper_fixture,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
