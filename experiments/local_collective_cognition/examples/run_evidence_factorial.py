"""Run the v0.20 Provider-source and Runtime-gate factorial."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_factorial import (  # noqa: E402
    FACTORIAL_TASK_KIND,
    analyze_factorial_run,
    run_factorial,
)
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderTelemetryLedger,
    hash_payload,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=str(
            REPO_ROOT / "outputs" / "evidence_factorial_calibration_v0_20"
        ),
    )
    parser.add_argument("--model", default="deepseek-r1:32b")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    output = Path(args.output_dir)
    corpus = read(output / "evidence_factorial_corpus_frozen.json")
    preregistration = read(
        output / "evidence_factorial_preregistration.json"
    )
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local-evidence-factorial",
        model_id=args.model,
        task_kinds=(FACTORIAL_TASK_KIND,),
        telemetry_ledger=ledger,
        base_url=args.base_url,
        timeout_seconds=600,
        max_new_tokens=650,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive="5m",
    )
    run = run_factorial(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_factorial_run(corpus=corpus, run=run)
    telemetry_commitment = {
        "telemetry_version": FACTORIAL_TASK_KIND,
        "items": [item.as_dict() for item in ledger.items()],
    }
    telemetry = {
        **telemetry_commitment,
        "artifact_hash": hash_payload(telemetry_commitment),
    }
    write(output / "evidence_factorial_run.json", run)
    write(output / "evidence_factorial_analysis.json", analysis)
    write(output / "evidence_factorial_telemetry.json", telemetry)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "source_call_coverage": analysis["source_call_coverage"],
        "cell_coverage": analysis["cell_coverage"],
        "failures": len(run["failures"]),
        "evidence_state_distributions": (
            analysis["evidence_state_distributions"]
        ),
        "definition_source_distributions": (
            analysis["definition_source_distributions"]
        ),
        "gate_transform_distributions": (
            analysis["gate_transform_distributions"]
        ),
        "structural_factor_effects": analysis["structural_factor_effects"],
        "source_token_ratio": (
            analysis["repaired_to_legacy_source_token_ratio"]
        ),
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
