"""Run the frozen v0.64 experiment one fail-closed stage at a time."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import (  # noqa: E402
    BoundedRetryProviderAdapter,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.selection_retention_fresh_binding_runtime import (  # noqa: E402
    analyze_fresh_binding_state,
    run_fresh_binding_panel,
    run_fresh_state_panel,
)
from local_collective_cognition.selection_retention_fresh_runtime import (  # noqa: E402
    analyze_retention_panel,
    analyze_selection_panel,
    build_delayed_consequence_packets,
    build_state_consensus_surface,
    run_retention_panel,
    run_selection_panel,
)


STAGES = ("binding", "state", "selection", "retention")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def adapter() -> BoundedRetryProviderAdapter:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    return BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-selection-retention-v0-64",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=STAGES)
    args = parser.parse_args()
    output = REPO_ROOT / "outputs" / "selection_retention_fresh_v0_64"
    corpus = read(output / "fresh_corpus_frozen.json")
    preregistration = read(output / "preregistration.json")
    provider = adapter()

    if args.stage == "binding":
        run = run_fresh_binding_panel(
            corpus=corpus,
            preregistration=preregistration,
            adapter=provider,
        )
        write(output / "binding_run.json", run)
        summary = {
            "stage": "binding",
            "receipts": len(run["raw_receipts"]),
            "relation_consensus": run[
                "binding_relation_consensus_count"
            ],
            "conflicts": len(run["binding_conflicts"]),
            "contract_failures": len(run["contract_failures"]),
            "auxiliary_divergences": len(
                run["auxiliary_evidence_divergences"]
            ),
            "next_stage_authorized": run[
                "binding_ready_for_state_assessment"
            ],
            "provider_tasks": len(run["task_calls"]),
            "tokens": sum(
                call["token_usage"]["total_tokens"]
                for call in run["task_calls"]
            ),
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    binding_run = read(output / "binding_run.json")
    if not binding_run["binding_ready_for_state_assessment"]:
        raise RuntimeError("binding gate failed; downstream is closed")
    if args.stage == "state":
        run = run_fresh_state_panel(
            corpus=corpus,
            preregistration=preregistration,
            binding_run=binding_run,
            adapter=provider,
        )
        write(output / "state_run.json", run)
        analysis = analyze_fresh_binding_state(
            corpus=corpus,
            preregistration=preregistration,
            binding_run=binding_run,
            state_run=run,
        )
        write(output / "binding_state_analysis.json", analysis)
        print(json.dumps({
            "stage": "state",
            "decision": analysis["decision"],
            "state_receipts": analysis["state_receipt_count"],
            "state_mismatches": len(
                analysis["state_reference_mismatches"]
            ),
            "state_disagreements": len(
                analysis["state_cross_role_disagreements"]
            ),
            "provider_tasks_cumulative": analysis[
                "provider_task_count"
            ],
            "tokens_cumulative": analysis["physical_total_tokens"],
            "next_stage_authorized": analysis[
                "selection_stage_authorized"
            ],
        }, indent=2, sort_keys=True))
        return 0

    state_run = read(output / "state_run.json")
    binding_state_analysis = read(output / "binding_state_analysis.json")
    if not binding_state_analysis["selection_stage_authorized"]:
        raise RuntimeError("state gate failed; downstream is closed")
    state_surface_path = output / "state_consensus_surface.json"
    if state_surface_path.exists():
        state_surface = read(state_surface_path)
    else:
        state_surface = build_state_consensus_surface(
            corpus=corpus,
            binding_run=binding_run,
            state_run=state_run,
            binding_state_analysis=binding_state_analysis,
        )
        write(state_surface_path, state_surface)
    if args.stage == "selection":
        run = run_selection_panel(
            corpus=corpus,
            preregistration=preregistration,
            state_surface=state_surface,
            adapter=provider,
        )
        write(output / "selection_run.json", run)
        analysis = analyze_selection_panel(
            corpus=corpus,
            preregistration=preregistration,
            selection_run=run,
        )
        write(output / "selection_analysis.json", analysis)
        print(json.dumps({
            "stage": "selection",
            "decision": analysis["decision"],
            "selection_receipts": analysis["selection_receipt_count"],
            "selection_consensus": analysis[
                "selection_consensus_count"
            ],
            "reference_mismatches": len(
                analysis["reference_mismatches"]
            ),
            "cross_role_disagreements": len(
                run["cross_role_disagreements"]
            ),
            "stage_tokens": sum(
                call["token_usage"]["total_tokens"]
                for call in run["task_calls"]
            ),
            "next_stage_authorized": analysis[
                "consequence_stage_authorized"
            ],
        }, indent=2, sort_keys=True))
        return 0

    selection_run = read(output / "selection_run.json")
    selection_analysis = read(output / "selection_analysis.json")
    if not selection_analysis["consequence_stage_authorized"]:
        raise RuntimeError("selection gate failed; downstream is closed")
    consequence_path = output / "consequence_packets.json"
    if consequence_path.exists():
        consequence_packets = read(consequence_path)
    else:
        consequence_packets = build_delayed_consequence_packets(
            corpus=corpus,
            selection_run=selection_run,
            selection_analysis=selection_analysis,
        )
        write(consequence_path, consequence_packets)
    run = run_retention_panel(
        corpus=corpus,
        preregistration=preregistration,
        selection_run=selection_run,
        consequence_packets=consequence_packets,
        adapter=provider,
    )
    write(output / "retention_run.json", run)
    analysis = analyze_retention_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        state_run=state_run,
        selection_run=selection_run,
        retention_run=run,
    )
    write(output / "retention_analysis.json", analysis)
    print(json.dumps({
        "stage": "retention",
        "decision": analysis["decision"],
        "retention_receipts": analysis["retention_receipt_count"],
        "retention_consensus": analysis["retention_consensus_count"],
        "reference_mismatches": len(
            analysis["retention_reference_mismatches"]
        ),
        "provider_tasks_cumulative": analysis["provider_task_count"],
        "physical_attempts_cumulative": analysis[
            "physical_attempt_count"
        ],
        "tokens_cumulative": analysis["physical_total_tokens"],
        "alpha_22_eligible": analysis["alpha_22_eligible"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
