"""Perform one same-contract recovery attempt for v0.17 structural failures."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_axis_routing import AXIS_TASK_KIND, analyze_axis_routing_run, recover_axis_routing_failures  # noqa: E402
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    output = REPO_ROOT / "outputs" / "axis_credibility_routing_v0_17"
    corpus = read(output / "axis_fresh_corpus_frozen.json")
    preregistration = read(output / "axis_routing_preregistration.json")
    role_run = read(output / "axis_role_run.json")
    role_analysis = read(output / "axis_role_analysis.json")
    run_path = output / "axis_routing_run.json"
    run = read(run_path)
    if not run.get("failures"):
        print(json.dumps({"state": "NO_RECOVERY_NEEDED", "run_hash": run["run_hash"]}, indent=2))
        return 0
    pre_recovery = output / "axis_routing_run_pre_recovery.json"
    if pre_recovery.exists():
        raise RuntimeError("axis_routing_recovery_already_attempted")
    shutil.copyfile(run_path, pre_recovery)
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local-axis-routing-recovery",
        model_id="deepseek-r1:32b",
        task_kinds=(AXIS_TASK_KIND,),
        telemetry_ledger=ledger,
        base_url="http://127.0.0.1:11434",
        timeout_seconds=600,
        max_new_tokens=700,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive="5m",
    )
    recovered = recover_axis_routing_failures(
        corpus=corpus,
        preregistration=preregistration,
        role_run=role_run,
        role_analysis=role_analysis,
        run=run,
        adapter=adapter,
    )
    analysis = analyze_axis_routing_run(corpus=corpus, role_analysis=role_analysis, run=recovered)
    telemetry_commitment = {"telemetry_version": AXIS_TASK_KIND + "_RECOVERY", "items": [item.as_dict() for item in ledger.items()]}
    write(run_path, recovered)
    write(output / "axis_routing_analysis.json", analysis)
    write(output / "axis_routing_recovery_telemetry.json", {**telemetry_commitment, "artifact_hash": hash_payload(telemetry_commitment)})
    print(json.dumps({
        "pre_recovery_run_hash": run["run_hash"],
        "recovered_run_hash": recovered["run_hash"],
        "residual_failures": len(recovered["failures"]),
        "recovery_history": recovered["recovery_history"],
        "coverage": analysis["coverage"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

