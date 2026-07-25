"""Generate the descriptive v0.89 semantic-veto versus failure audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.factorized_benchmarks.scifact_v0_89_posthoc import (  # noqa: E402
    build_binding_veto_posthoc,
)


def main() -> None:
    output = ROOT / "outputs" / "scifact_claim_atom_binding_v0_89"
    audit = build_binding_veto_posthoc(
        panel=_read(output / "holdout_private.json"),
        scope_run=_read(output / "scope_run.json"),
        binding_run=_read(output / "binding_run.json"),
        challenge_run=_read(output / "challenge_run.json"),
        candidate_run=_read(output / "candidate_run.json"),
        evaluation=_read(output / "evaluation.json"),
    )
    target = output / "posthoc_audit.json"
    target.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: audit[key] for key in (
            "provider_binding_failure_count",
            "downstream_propagated_failure_count",
            "unique_failed_case_count",
            "valid_semantic_veto_count",
            "valid_semantic_correct_harm_veto_count",
            "valid_semantic_false_veto_count",
            "fail_closed_harmful_baseline_count",
            "refutation_polarity_asymmetry_count",
            "descriptive_posthoc_only",
            "gate_authority",
            "artifact_hash",
        )
    }, indent=2))


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
