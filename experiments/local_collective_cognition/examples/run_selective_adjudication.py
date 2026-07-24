"""Run focused provider adjudication for v0.18 admitted objects."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_selective_runtime import (  # noqa: E402
    SELECTIVE_TASK_KIND,
    analyze_selective_run,
    run_selective_adjudication,
)
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "selective_escalation_v0_18"))
    parser.add_argument("--model", default="deepseek-r1:32b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    output = Path(args.output_dir)
    corpus = read(output / "selective_fresh_corpus_frozen.json")
    preregistration = read(output / "selective_preregistration.json")
    baseline = read(output / "selective_baseline_run.json")
    plan = read(output / "selective_admission_plan.json")
    local = read(output / "selective_local_role_run.json")
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local-selective-adjudicator",
        model_id=args.model,
        task_kinds=(SELECTIVE_TASK_KIND,),
        telemetry_ledger=ledger,
        base_url=args.base_url,
        timeout_seconds=600,
        max_new_tokens=500,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive="5m",
    )
    run = run_selective_adjudication(
        corpus=corpus,
        preregistration=preregistration,
        baseline_run=baseline,
        admission_plan=plan,
        local_role_run=local,
        adapter=adapter,
    )
    analysis = analyze_selective_run(
        corpus=corpus,
        baseline_run=baseline,
        admission_plan=plan,
        local_role_run=local,
        run=run,
    )
    telemetry_commitment = {
        "telemetry_version": SELECTIVE_TASK_KIND + "_ADJUDICATION",
        "items": [item.as_dict() for item in ledger.items()],
    }
    telemetry = {**telemetry_commitment, "artifact_hash": hash_payload(telemetry_commitment)}
    write(output / "selective_adjudication_run.json", run)
    write(output / "selective_analysis.json", analysis)
    write(output / "selective_adjudication_telemetry.json", telemetry)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "admitted_count": analysis["admitted_count"],
        "successful_adjudication_count": analysis["successful_adjudication_count"],
        "failure_count": len(run["failures"]),
        "routed_coverage": analysis["routed_coverage"],
        "token_ratio": analysis["routed_to_baseline_token_ratio"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
