"""Freeze v0.54 corpus and source artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.evidence_first_holdout import (  # noqa: E402
    build_evidence_first_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def verify(value):
    commitment = {
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value["artifact_hash"] != hash_payload(commitment):
        raise ValueError("source_hash_invalid")


def main():
    source = REPO_ROOT / "outputs" / "context_qualification_v0_53"
    output = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    output.mkdir(parents=True, exist_ok=True)
    sources = (
        (
            "source_v0_53_preregistration.json",
            "context_qualification_preregistration.json",
        ),
        (
            "source_v0_53_analysis.json",
            "context_qualification_analysis.json",
        ),
        ("source_v0_53_closure.json", "closure.json"),
        (
            "source_v0_53_posthoc.json",
            "posthoc_context_qualification.json",
        ),
        (
            "source_unlabeled_qualification_calibration.json",
            "unlabeled_qualification_calibration.json",
        ),
    )
    for target, source_name in sources:
        value = read(source / source_name)
        verify(value)
        write(output / target, value)
    corpus = build_evidence_first_holdout()
    write(output / "evidence_first_corpus_frozen.json", corpus)
    stale = (
        "reference_completeness_audit.json",
        "evidence_first_preregistration.json",
        "evidence_first_run.json",
        "evidence_first_analysis.json",
        "posthoc_evidence_first.json",
        "closure.json",
    )
    for name in stale:
        path = output / name
        if path.exists():
            path.unlink()
    for path in output.glob("*progress.json"):
        path.unlink()
    for path in output.glob("*return_pack.zip"):
        path.unlink()
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "case_count": corpus["case_count"],
        "source_count": len(sources),
        "formal_run_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
