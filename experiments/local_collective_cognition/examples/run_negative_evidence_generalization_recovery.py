"""Run the frozen v0.2.1 transport recovery with local heterogeneous live audit."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import (  # noqa: E402
    BoundedRetryProviderAdapter,
)
from local_collective_cognition.negative_evidence_audit_contracts import (  # noqa: E402
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
)
from local_collective_cognition.negative_evidence_generalization_fusion import (  # noqa: E402
    BASELINE,
    HETEROGENEOUS_LIVE,
    MONOLITHIC_REPEAT_2,
    MONOLITHIC_REPEAT_3,
    SAME_MODEL_LIVE,
    SHARED_FABRICATION,
)
from local_collective_cognition.negative_evidence_generalization_holdout import (  # noqa: E402
    validate_generalization_corpus_artifact,
)
from local_collective_cognition.negative_evidence_generalization_runtime import (  # noqa: E402
    NegativeEvidenceGeneralizationRuntime,
    validate_generalization_candidate_run,
)
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderTelemetryLedger,
    hash_payload,
)
from local_collective_cognition.structure_semantic_judge_contracts import (  # noqa: E402
    JUDGE_TASK_KIND,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _deepseek(provider_id, task_kind, max_tokens, max_attempts):
    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id, "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY",
        (task_kind,), max_tokens=max_tokens, timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    return BoundedRetryProviderAdapter(adapter, max_attempts=max_attempts)


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_generalization_v0_2"
    parser.add_argument(
        "--corpus", default=f"{base}/private_negative_generalization_corpus.json",
    )
    parser.add_argument(
        "--contract", default=f"{base}/transport_recovery_contract_v0_2_1.json",
    )
    parser.add_argument(
        "--output", default=f"{base}/four_arm_candidate_run_v0_2_1.json",
    )
    args = parser.parse_args()
    corpus = json.loads(_resolve(args.corpus).read_text(encoding="utf-8"))
    contract = json.loads(_resolve(args.contract).read_text(encoding="utf-8"))
    validate_generalization_corpus_artifact(corpus)
    committed = {key: value for key, value in contract.items() if key != "contract_hash"}
    if (
        contract.get("contract_hash") != hash_payload(committed)
        or contract.get("corpus_artifact_hash") != corpus["artifact_hash"]
        or contract.get("panel_labels_available") is not False
        or contract.get("gate_changes_allowed") is not False
    ):
        raise ValueError("negative_generalization_recovery_contract_invalid")
    max_attempts = contract["allowed_changes"]["maximum_same_contract_transport_attempts"]
    ledger = ProviderTelemetryLedger()
    adapters = {
        BASELINE: _deepseek("deepseek-recovery-baseline", JUDGE_TASK_KIND, 2600, max_attempts),
        MONOLITHIC_REPEAT_2: _deepseek(
            "deepseek-recovery-monolithic-r2", JUDGE_TASK_KIND, 2600, max_attempts,
        ),
        MONOLITHIC_REPEAT_3: _deepseek(
            "deepseek-recovery-monolithic-r3", JUDGE_TASK_KIND, 2600, max_attempts,
        ),
        SAME_MODEL_LIVE: _deepseek(
            "deepseek-recovery-live", TASK_KINDS[LIVE_AMBIGUITY_AUDIT],
            1800, max_attempts,
        ),
        SHARED_FABRICATION: _deepseek(
            "deepseek-recovery-fabrication", TASK_KINDS[FABRICATION_AUDIT],
            1800, max_attempts,
        ),
        HETEROGENEOUS_LIVE: OllamaJsonAdapter(
            provider_id="ollama-recovery-live",
            model_id="deepseek-r1:32b",
            task_kinds=(TASK_KINDS[LIVE_AMBIGUITY_AUDIT],),
            telemetry_ledger=ledger,
            timeout_seconds=900,
            max_new_tokens=1800,
            max_attempts=max_attempts,
            thinking_enabled=False,
            keep_alive="15m",
        ),
    }
    experiment_id = "negative-generalization-recovery-" + datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")
    run = NegativeEvidenceGeneralizationRuntime(
        corpus_artifact=corpus,
    ).evaluate(experiment_id=experiment_id, adapters=adapters)
    commitment = {
        "transport_recovery_contract_hash": contract["contract_hash"],
        "predecessor_candidate_run_hash": contract["predecessor_candidate_run_hash"],
        "candidate_run": run,
    }
    artifact = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_generalization_candidate_run(run, corpus_artifact=corpus)
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    records = run["fusion"]["records"]
    print(json.dumps({
        "artifact_hash": artifact["artifact_hash"],
        "candidate_run_hash": run["candidate_run_hash"],
        "total_unique_provider_calls": run["total_unique_provider_calls"],
        "total_unique_tokens": run["total_unique_input_tokens"] + run["total_unique_output_tokens"],
        "lane_failures": {
            lane: len(value["failures"]) for lane, value in run["lanes"].items()
        },
        "arm_states": {
            "SINGLE_MONOLITHIC": dict(Counter(
                item["single_monolithic_state"] for item in records
            )),
            "BUDGET_MATCHED_MONOLITHIC": dict(Counter(
                item["budget_matched_monolithic_state"] for item in records
            )),
            "SAME_MODEL_SPLIT": dict(Counter(
                item["same_model_split_state"] for item in records
            )),
            "HETEROGENEOUS_SPLIT": dict(Counter(
                item["heterogeneous_split_state"] for item in records
            )),
        },
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
