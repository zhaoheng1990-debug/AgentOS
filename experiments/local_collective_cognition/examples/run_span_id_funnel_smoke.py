"""Run the v0.25 immutable span-ID funnel smoke on local DeepSeek."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_span_id_funnel import (  # noqa: E402
    FUNNEL_TASK_KIND,
    analyze_span_id_funnel_smoke,
    run_span_id_funnel_smoke,
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
    output = REPO_ROOT / "outputs" / "span_id_funnel_v0_25"
    corpus = read(output / "span_id_funnel_corpus_frozen.json")
    preregistration = read(output / "span_id_funnel_preregistration.json")
    ledger = ProviderTelemetryLedger()
    adapter = OllamaJsonAdapter(
        provider_id="ollama-local-span-id-funnel",
        model_id="deepseek-r1:32b",
        task_kinds=(FUNNEL_TASK_KIND,),
        telemetry_ledger=ledger,
        base_url="http://127.0.0.1:11434",
        timeout_seconds=600,
        max_new_tokens=600,
        max_attempts=2,
        thinking_enabled=False,
        keep_alive="5m",
    )
    run = run_span_id_funnel_smoke(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_span_id_funnel_smoke(
        corpus=corpus,
        run=run,
        preregistration=preregistration,
    )
    telemetry_commitment = {
        "telemetry_version": FUNNEL_TASK_KIND,
        "items": [item.as_dict() for item in ledger.items()],
    }
    telemetry = {
        **telemetry_commitment,
        "artifact_hash": hash_payload(telemetry_commitment),
    }
    write(output / "span_id_funnel_run.json", run)
    write(output / "span_id_funnel_analysis.json", analysis)
    write(output / "span_id_funnel_telemetry.json", telemetry)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "span_pack_validation_rate": analysis["span_pack_validation_rate"],
        "source_candidate_blind_rate": (
            analysis["source_candidate_blind_rate"]
        ),
        "source_receipt_validation_rate": (
            analysis["source_receipt_validation_rate"]
        ),
        "source_status_construction_match_rate": (
            analysis["source_status_construction_match_rate"]
        ),
        "false_available_promotion_count": (
            analysis["false_available_promotion_count"]
        ),
        "source_status_distribution": analysis["source_status_distribution"],
        "entailment_call_count": analysis["entailment_call_count"],
        "entailment_receipt_validation_rate": (
            analysis["entailment_receipt_validation_rate"]
        ),
        "no_new_span_id_rate": analysis["no_new_span_id_rate"],
        "output_coverage": analysis["output_coverage"],
        "provider_call_count": analysis["provider_call_count"],
        "failure_counts": analysis["failure_counts"],
        "total_tokens": analysis["total_tokens"],
        "gate_conditions": analysis["preregistered_gate_conditions"],
        "structural_smoke_gate": analysis["structural_smoke_gate"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
