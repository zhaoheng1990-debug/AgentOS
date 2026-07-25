"""Freeze and run atomic witness admission v0.80."""

import argparse
import json
import sys
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v2_runtime import (  # noqa: E402
    run_typed_admission_panel,
)
from local_collective_cognition.admission_v5_evaluation import (  # noqa: E402
    build_pre_reference_evaluation,
)
from local_collective_cognition.admission_v5_fresh_holdout import (  # noqa: E402
    build_fresh_holdout,
    build_preregistration,
    public_fresh_holdout,
    validate_fresh_holdout,
    validate_preregistration,
)
from local_collective_cognition.admission_v5_runtime import (  # noqa: E402
    run_atomic_witness_panel,
)
from local_collective_cognition.benchmark_bridge_provider import (  # noqa: E402
    build_deepseek_adapter,
)
from local_collective_cognition.benchmark_bridge_sources import (  # noqa: E402
    ensure_holdout_source,
    ensure_sources,
    holdout_source_manifest,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        required=True,
        choices=("freeze", "baseline", "candidate", "score"),
    )
    stage = parser.parse_args().stage
    output = ROOT / "outputs" / "admission_v5_fresh_holdout_v0_80"
    output.mkdir(parents=True, exist_ok=True)

    if stage == "freeze":
        paths = ensure_sources()
        paths["test_article_ids.txt"] = ensure_holdout_source()
        panel = build_fresh_holdout(
            paths,
            source_manifest=holdout_source_manifest(),
        )
        preregistration = build_preregistration(panel)
        write(output / "holdout_private.json", panel)
        write(output / "holdout_public.json", public_fresh_holdout(panel))
        write(output / "preregistration.json", preregistration)
        print(json.dumps({
            "panel_hash": panel["artifact_hash"],
            "preregistration_hash": preregistration["artifact_hash"],
            "case_count": panel["case_count"],
            "label_balance": panel["label_balance"],
            "provider_calls": 0,
        }, indent=2))
        return

    panel = read(output / "holdout_private.json")
    preregistration = read(output / "preregistration.json")
    validate_fresh_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    if stage == "baseline":
        run = run_typed_admission_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_adapter(),
        )
        write(output / "baseline_run.json", run)
        print(json.dumps(_run_summary(run), indent=2))
        return
    if stage == "candidate":
        run = run_atomic_witness_panel(
            panel=panel,
            preregistration=preregistration,
            adapter=build_deepseek_adapter(),
        )
        write(output / "candidate_run.json", run)
        print(json.dumps(_run_summary(run), indent=2))
        return
    evaluation = build_pre_reference_evaluation(
        panel=panel,
        preregistration=preregistration,
        baseline_run=read(output / "baseline_run.json"),
        candidate_run=read(output / "candidate_run.json"),
    )
    write(output / "pre_reference_evaluation.json", evaluation)
    print(json.dumps({
        "baseline": _score_summary(evaluation["baseline"]),
        "candidate": _score_summary(evaluation["candidate"]),
        "improved_case_ids": evaluation["improved_case_ids"],
        "harmed_case_ids": evaluation["harmed_case_ids"],
        "semantic_conflict_span_count": (
            evaluation["semantic_conflict_span_count"]
        ),
        "semantic_conflict_code_counts": (
            evaluation["semantic_conflict_code_counts"]
        ),
        "operational_conditions": (
            evaluation["operational_conditions"]
        ),
        "operational_decision": evaluation["operational_decision"],
        "semantic_decision": evaluation["semantic_decision"],
    }, indent=2))


def _run_summary(run):
    return {
        "receipts": len(run["receipts"]),
        "partitions": len(run["partitions"]),
        "contract_failures": len(run["contract_failures"]),
        "compiler_failures": len(run["compiler_failures"]),
        "tasks": len(run["task_calls"]),
    }


def _score_summary(value):
    return {
        key: value[key] for key in (
            "valid_receipt_count",
            "failure_count",
            "complete_partition_count",
            "evidence_precision",
            "evidence_recall",
            "evidence_f1",
            "provider_task_count",
            "physical_attempt_count",
            "physical_total_tokens",
        )
    }


if __name__ == "__main__":
    main()
