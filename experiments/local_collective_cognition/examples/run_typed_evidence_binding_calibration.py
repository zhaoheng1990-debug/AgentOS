"""Run the frozen v0.63 typed evidence-binding calibration."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.typed_evidence_binding_contracts import (  # noqa: E402
    build_typed_preregistration,
)
from local_collective_cognition.typed_evidence_binding_runtime import (  # noqa: E402
    analyze_typed_state_panel,
    run_typed_binding_panel,
    run_typed_state_panel,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    source = REPO_ROOT / "outputs" / "portfolio_critic_fresh_v0_61_1"
    predecessor = (
        REPO_ROOT / "outputs" / "relation_evidence_binding_v0_62_1"
    )
    output = REPO_ROOT / "outputs" / "typed_evidence_binding_v0_63"
    output.mkdir(parents=True, exist_ok=True)
    corpus = read(source / "fresh_corpus_frozen.json")
    source_closure = read(predecessor / "closure.json")
    preregistration = build_typed_preregistration(
        corpus=corpus,
        source_closure=source_closure,
    )
    write(output / "preregistration.json", preregistration)
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-typed-evidence-binding-v0-63",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=4200,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    binding_run = run_typed_binding_panel(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    write(output / "binding_run.json", binding_run)
    summary = {
        "binding_receipts": len(binding_run["raw_receipts"]),
        "binding_relation_consensus": binding_run[
            "binding_relation_consensus_count"
        ],
        "binding_conflicts": len(binding_run["binding_conflicts"]),
        "binding_contract_failures": len(
            binding_run["contract_failures"]
        ),
        "auxiliary_evidence_divergences": len(
            binding_run["auxiliary_evidence_divergences"]
        ),
        "binding_ready": binding_run[
            "binding_ready_for_state_assessment"
        ],
    }
    if not binding_run["binding_ready_for_state_assessment"]:
        summary.update({
            "decision": "REJECT_TYPED_EVIDENCE_BINDING_CONSENSUS_GATE",
            "state": "TYPED_BINDING_CONSENSUS_INSUFFICIENT_STOP",
            "state_stage_executed": False,
        })
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    state_run = run_typed_state_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        adapter=adapter,
    )
    write(output / "state_run.json", state_run)
    analysis = analyze_typed_state_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        state_run=state_run,
    )
    write(output / "analysis.json", analysis)
    summary.update({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "state_receipts": analysis["state_receipt_count"],
        "state_contract_failures": len(state_run["contract_failures"]),
        "state_mismatches": len(
            analysis["state_reference_mismatches"]
        ),
        "state_disagreements": len(
            analysis["state_cross_role_disagreements"]
        ),
        "required_coordinate_recovered": analysis[
            "required_coordinate_recovered"
        ],
        "provider_calls": analysis["provider_call_count"],
        "tokens": analysis["physical_total_tokens"],
        "core_contract_sync_eligible": analysis[
            "core_contract_sync_eligible"
        ],
    })
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
