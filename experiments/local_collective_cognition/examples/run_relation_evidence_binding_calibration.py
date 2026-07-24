"""Run the frozen v0.62 two-stage binding calibration."""

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
from local_collective_cognition.relation_evidence_binding_calibration import (  # noqa: E402
    analyze_state_panel,
    build_binding_preregistration,
    run_binding_panel,
    run_state_panel,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    revision = os.environ.get("AGENTOS_BINDING_REVISION", "v0_62")
    if revision not in {"v0_62", "v0_62_1"}:
        raise ValueError("binding_revision_invalid")
    source = (
        REPO_ROOT / "outputs" / "portfolio_critic_fresh_v0_61_1"
    )
    output = (
        REPO_ROOT / "outputs" / f"relation_evidence_binding_{revision}"
    )
    output.mkdir(parents=True, exist_ok=True)
    corpus = read(source / "fresh_corpus_frozen.json")
    failed_reference = read(
        source / "reference_completeness_audit.json"
    )
    source_closure = read(source / "closure.json")
    preregistration = build_binding_preregistration(
        corpus=corpus,
        failed_reference=failed_reference,
        source_closure=source_closure,
        runtime_version=f"relation_evidence_binding_calibration_{revision}",
        coarse_identity_consensus=revision == "v0_62_1",
        provider_binding_state_authority=revision != "v0_62_1",
    )
    write(output / "preregistration.json", preregistration)
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-relation-evidence-binding-v0-62",
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
    binding_run = run_binding_panel(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    write(output / "binding_run.json", binding_run)
    result = {
        "revision": revision,
        "binding_receipts": len(binding_run["raw_receipts"]),
        "binding_subtype_divergences": len(
            binding_run["binding_subtype_divergences"]
        ),
        "binding_relation_consensus": binding_run[
            "binding_relation_consensus_count"
        ],
        "binding_conflicts": len(binding_run["binding_conflicts"]),
        "binding_contract_failures": len(
            binding_run["contract_failures"]
        ),
        "binding_ready": binding_run[
            "binding_ready_for_state_assessment"
        ],
    }
    if binding_run["binding_ready_for_state_assessment"]:
        state_run = run_state_panel(
            corpus=corpus,
            preregistration=preregistration,
            binding_run=binding_run,
            adapter=adapter,
        )
        write(output / "state_run.json", state_run)
        analysis = analyze_state_panel(
            corpus=corpus,
            preregistration=preregistration,
            binding_run=binding_run,
            state_run=state_run,
        )
        write(output / "analysis.json", analysis)
        result.update({
            "decision": analysis["decision"],
            "state": analysis["candidate_state"],
            "state_receipts": analysis["state_receipt_count"],
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
            "fresh_generalization_claim": False,
        })
    else:
        result.update({
            "decision": "REJECT_BINDING_CONSENSUS_GATE",
            "state": "BINDING_CONSENSUS_INSUFFICIENT_STOP",
            "state_stage_executed": False,
        })
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
