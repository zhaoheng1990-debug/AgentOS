"""Run blind baseline, coordinator, basis critic, and routed v0.17 arms."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_axis_routing import AXIS_TASK_KIND, analyze_axis_routing_run, run_axis_routing_arms  # noqa: E402
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "axis_credibility_routing_v0_17"))
    parser.add_argument("--model", default="deepseek-r1:32b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    output = Path(args.output_dir)
    corpus = read(output / "axis_fresh_corpus_frozen.json")
    preregistration = read(output / "axis_routing_preregistration.json")
    role_run = read(output / "axis_role_run.json")
    role_analysis = read(output / "axis_role_analysis.json")
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local-axis-routing",
        model_id=args.model,
        task_kinds=(AXIS_TASK_KIND,),
        telemetry_ledger=ledger,
        base_url=args.base_url,
        timeout_seconds=600,
        max_new_tokens=700,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive="5m",
    )
    run = run_axis_routing_arms(
        corpus=corpus,
        preregistration=preregistration,
        role_run=role_run,
        role_analysis=role_analysis,
        adapter=adapter,
    )
    analysis = analyze_axis_routing_run(corpus=corpus, role_analysis=role_analysis, run=run)
    telemetry_commitment = {"telemetry_version": AXIS_TASK_KIND, "items": [item.as_dict() for item in ledger.items()]}
    telemetry = {**telemetry_commitment, "artifact_hash": hash_payload(telemetry_commitment)}
    write(output / "axis_routing_run.json", run)
    write(output / "axis_routing_analysis.json", analysis)
    write(output / "axis_routing_telemetry.json", telemetry)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "coverage": analysis["coverage"],
        "failures": len(run["failures"]),
        "candidate_state": analysis["candidate_state"],
        "routed_to_baseline_token_ratio": analysis["routed_to_baseline_token_ratio"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())

