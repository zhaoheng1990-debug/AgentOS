"""Run local DeepSeek baseline and role-informed coordinator on the frozen fresh set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_coordinator import COORDINATOR_TASK_KIND, analyze_blind_coordinator_arms, run_blind_coordinator_arms  # noqa: E402
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger, hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    parser.add_argument("--model", default="deepseek-r1:32b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    output = Path(args.output_dir)
    corpus = read(output / "fresh_action_corpus_frozen.json")
    role_run = read(output / "fresh_action_role_run.json")
    role_analysis = read(output / "fresh_action_role_analysis.json")
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(provider_id="ollama-local-cognitive-action", model_id=args.model, task_kinds=(COORDINATOR_TASK_KIND,), telemetry_ledger=ledger, base_url=args.base_url, timeout_seconds=600, max_new_tokens=900, max_attempts=2, thinking_enabled=False, keep_alive="5m")
    run = run_blind_coordinator_arms(corpus=corpus, role_run=role_run, role_analysis=role_analysis, adapter=adapter)
    analysis = analyze_blind_coordinator_arms(corpus=corpus, role_run=role_run, role_analysis=role_analysis, run=run)
    telemetry_commitment = {"telemetry_version": COORDINATOR_TASK_KIND, "items": [item.as_dict() for item in ledger.items()]}
    telemetry = {**telemetry_commitment, "artifact_hash": hash_payload(telemetry_commitment)}
    write(output / "blind_coordinator_arms_run.json", run)
    write(output / "blind_coordinator_arms_analysis.json", analysis)
    write(output / "blind_coordinator_telemetry.json", telemetry)
    print(json.dumps({"run_hash": run["run_hash"], "analysis_hash": analysis["artifact_hash"], "arm_coverage": analysis["arm_coverage"], "disagreement_count": analysis["full_tuple_disagreement_count"], "accounting": analysis["accounting"], "candidate_state": analysis["candidate_state"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

