"""Run the v0.22 evidence-first selective challenge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_evidence_first import (  # noqa: E402
    EVIDENCE_FIRST_TASK_KIND,
    analyze_evidence_first_run,
    run_evidence_first_selective,
)
from local_collective_cognition.ollama_provider import (  # noqa: E402
    OllamaJsonAdapter,
)
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
    output = REPO_ROOT / "outputs" / "evidence_first_selective_v0_22"
    corpus = read(output / "evidence_first_corpus_frozen.json")
    preregistration = read(output / "evidence_first_preregistration.json")
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local-evidence-first",
        model_id="deepseek-r1:32b",
        task_kinds=(EVIDENCE_FIRST_TASK_KIND,),
        telemetry_ledger=ledger,
        base_url="http://127.0.0.1:11434",
        timeout_seconds=600,
        max_new_tokens=750,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive="5m",
    )
    run = run_evidence_first_selective(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_evidence_first_run(corpus=corpus, run=run)
    telemetry_commitment = {
        "telemetry_version": EVIDENCE_FIRST_TASK_KIND,
        "items": [item.as_dict() for item in ledger.items()],
    }
    telemetry = {
        **telemetry_commitment,
        "artifact_hash": hash_payload(telemetry_commitment),
    }
    write(output / "evidence_first_run.json", run)
    write(output / "evidence_first_analysis.json", analysis)
    write(output / "evidence_first_telemetry.json", telemetry)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "challenge_plan": run["challenge_plan"],
        "cell_coverage": analysis["cell_coverage"],
        "completed_challenges": analysis["completed_challenge_count"],
        "witness_validation_rate": analysis["witness_validation_rate"],
        "changed_axis_counts": analysis["changed_axis_counts"],
        "changed_object_count": analysis["changed_object_count"],
        "failure_counts": analysis["failure_counts"],
        "selective_to_baseline_token_ratio": (
            analysis["selective_to_baseline_token_ratio"]
        ),
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
