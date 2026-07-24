"""Run the zero-Provider v0.55 relation-stability audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.relation_stability_audit import (  # noqa: E402
    audit_relation_stability,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    source = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    output = REPO_ROOT / "outputs" / "relation_stability_audit_v0_55"
    output.mkdir(parents=True, exist_ok=True)
    audit = audit_relation_stability(
        corpus=read(source / "evidence_first_corpus_frozen.json"),
        run=read(source / "evidence_first_run.json"),
        posthoc=read(source / "posthoc_evidence_first.json"),
    )
    write(output / "relation_stability_audit.json", audit)
    print(json.dumps({
        "diagnosis": audit["diagnosis"],
        "baseline": audit["arm_summaries"]["A1_BASELINE"],
        "experimental": audit["arm_summaries"]["A2_COMPACT_DELTA"],
        "provider_calls_added": audit["provider_calls_added"],
        "formal_v0_54_decision_unchanged": audit[
            "formal_v0_54_decision_unchanged"
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
