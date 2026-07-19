"""Live four-role cognitive-agent smoke test over the LIFE-COG3R source pack."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE_ROOT.parent
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import AgentDescriptor, ProviderTaskRouter  # noqa: E402
from agentos_runtime import (  # noqa: E402
    CognitiveAgent,
    CognitiveCoordinationRuntime,
    CognitiveDeliberationSession,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)
from examples.project_source_group_cognition_smoke import (  # noqa: E402
    EXPECTED_CLASSIFICATION,
    EXPECTED_LOCAL_RULES,
    LiveProviderSpec,
    OpenAICompatibleJsonAdapter,
    default_paths,
    load_source_dossier,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _canonical_rules(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    labels: set[str] = set()
    for value in values:
        text = str(value)
        for label in EXPECTED_LOCAL_RULES:
            if label in text:
                labels.add(label)
    return labels


def latest_receipts_by_stage(receipts: tuple[Any, ...]) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    for receipt in receipts:
        latest[receipt.stage] = receipt
    return latest


def _provider_specs() -> dict[str, LiveProviderSpec]:
    return {
        "HYPOTHESIS_GENERATOR": LiveProviderSpec(
            "deepseek",
            "deepseek-v4-flash",
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            "group_hypothesis_generation",
            2500,
            {"thinking": {"type": "disabled"}},
        ),
        "ADVERSARIAL_REVIEWER": LiveProviderSpec(
            "moonshot",
            "kimi-k2.5",
            "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY",
            "adversarial_epistemic_review",
            6000,
            {},
        ),
        "REPLICATOR": LiveProviderSpec(
            "deepseek",
            "deepseek-v4-pro",
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            "independent_replication_interpretation",
            3000,
            {"thinking": {"type": "disabled"}},
        ),
        "SYNTHESIZER": LiveProviderSpec(
            "moonshot",
            "kimi-k2.5",
            "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY",
            "group_synthesis_and_conflict_resolution",
            4000,
            {},
        ),
    }


def _coordinator_spec() -> LiveProviderSpec:
    return LiveProviderSpec(
        "deepseek",
        "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        "cognitive_deliberation_coordination",
        1800,
        {"thinking": {"type": "disabled"}},
    )


def run_smoke(
    source_pack: Path,
    gate_file: Path,
    output_dir: Path,
    *,
    coordinated: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dossier, source_inventory = load_source_dossier(source_pack, gate_file)
    _write_json(output_dir / "source_hash_inventory.json", source_inventory)
    source_refs = tuple(dossier["source_refs"])
    specs = _provider_specs()
    roles = tuple(specs)
    agents: list[CognitiveAgent] = []
    adapters = {}
    for index, role in enumerate(roles, start=1):
        spec = specs[role]
        descriptor = AgentDescriptor(
            agent_id=f"{role.lower().replace('_', '-')}-{spec.model_id}",
            role=role,
            capabilities=("semantic_judgment", "source_read"),
            runner_id=f"agentos-runtime-role-{index}",
            harness_id=f"project-source-harness-{index}",
            provider_id=spec.provider_id,
            context_isolation_key=f"life-cog3r-{role.lower()}-context",
            allowed_evidence_scopes=("project://LIFE_COG3R",),
        )
        cognitive_agent = CognitiveAgent(
            descriptor,
            standard_role_contract(role),
            model_id=spec.model_id,
            private_memory_namespace=f"life-cog3r-{role.lower()}-memory",
            harness_capabilities=("source_read", "formal_receipt_write"),
            credit_subject_id=f"credit-{descriptor.agent_id}",
        )
        agents.append(cognitive_agent)
        adapters[cognitive_agent.agent_id] = ProviderCognitiveAgentAdapter(
            f"live-{role.lower()}-adapter",
            ProviderTaskRouter(
                [OpenAICompatibleJsonAdapter(spec), OpenAICompatibleJsonAdapter(spec)]
            ),
        )

    coordinator = None
    coordination_runtime = None
    if coordinated:
        spec = _coordinator_spec()
        descriptor = AgentDescriptor(
            agent_id=f"cognitive-coordinator-{spec.model_id}",
            role="COORDINATOR",
            capabilities=("semantic_judgment", "formal_receipt_read", "route_proposal"),
            runner_id="agentos-runtime-coordinator",
            harness_id="project-source-coordination-harness",
            provider_id=spec.provider_id,
            context_isolation_key="life-cog3r-coordinator-context",
            allowed_evidence_scopes=("project://LIFE_COG3R",),
        )
        coordinator = CognitiveAgent(
            descriptor,
            standard_role_contract("COORDINATOR"),
            model_id=spec.model_id,
            private_memory_namespace="life-cog3r-coordinator-memory",
            harness_capabilities=("formal_receipt_read", "route_proposal"),
            credit_subject_id=f"credit-{descriptor.agent_id}",
        )
        coordination_runtime = CognitiveCoordinationRuntime(
            coordinator=coordinator,
            adapter=ProviderCognitiveAgentAdapter(
                "live-coordinator-adapter",
                ProviderTaskRouter(
                    [OpenAICompatibleJsonAdapter(spec), OpenAICompatibleJsonAdapter(spec)]
                ),
            ),
            workspace_root=output_dir / "coordinator_private_workspace",
            max_cycles=10,
            max_role_executions_per_role=2,
        )

    objective = (
        "Assess the overbroad claim 'LIFE_COG3R proves validation-gated retention improves future adaptation' "
        "against the frozen project evidence. Preserve the descriptive local G4 observations for DayNight and "
        "HighLife while rejecting any unsupported overall retention, causal, aligned-Cbit, or ontological promotion."
    )
    assertions = {
        "ADVERSARIAL_REVIEWER": (
            {
                "assertion_id": "review-state-frozen",
                "path": "recommended_epistemic_state",
                "operator": "equals",
                "expected": "FALSIFIED",
                "evidence_refs": list(source_refs),
            },
        ),
        "REPLICATOR": (
            {
                "assertion_id": "replication-outcome-frozen",
                "path": "replication_outcome",
                "operator": "equals",
                "expected": "FAILED",
                "evidence_refs": list(source_refs),
            },
        ),
    }
    bounded_evidence_payload = {
        "source_project": dossier["source_project"],
        "evidence_coordinate": dossier["evidence_coordinate"],
        "frozen_acceptance_gates": dossier["frozen_acceptance_gates"],
        "machine_verdict": dossier["machine_verdict"],
        "independent_structural_qa": dossier["independent_structural_qa"],
        "source_refs": dossier["source_refs"],
    }
    session = CognitiveDeliberationSession(
        session_id=(
            "life-cog3r-coordinated-live"
            if coordinated
            else "life-cog3r-four-role-live"
        ),
        objective=objective,
        project_scope="project://LIFE_COG3R",
        frozen_gate_refs=(str(gate_file.resolve()),),
        evidence_refs=source_refs,
        evidence_payload=bounded_evidence_payload,
        agents=tuple(agents),
        adapters=adapters,
        workspace_root=output_dir / "private_agent_workspaces",
        kernel_authorization_ref="kernel-authorization://life-cog3r-four-role-smoke",
        consistency_assertions_by_role=assertions,
        coordination_runtime=coordination_runtime,
    )
    snapshot = session.run_to_candidate(max_retries_per_stage=2)
    _write_json(output_dir / "deliberation_snapshot.json", snapshot.as_dict())
    _write_json(
        output_dir / "cognitive_team.json",
        {
            "agents": [agent.as_dict() for agent in agents],
            "coordinator": coordinator.as_dict() if coordinator else None,
        },
    )

    messages = {message.sender_role: message for message in snapshot.messages}
    reviewer = messages.get("ADVERSARIAL_REVIEWER")
    replicator = messages.get("REPLICATOR")
    synthesizer = messages.get("SYNTHESIZER")
    synth_claims = synthesizer.payload.get("converged_claims", []) if synthesizer else []
    latest_receipts = latest_receipts_by_stage(snapshot.execution_receipts)
    final_role_receipts = tuple(
        latest_receipts.get(stage)
        for stage in ("GENERATION", "REVIEW", "REPLICATION", "SYNTHESIS")
    )
    gates = {
        "source_machine_classification_frozen": dossier["machine_verdict"].get("machine_classification")
        == EXPECTED_CLASSIFICATION,
        "exactly_four_independent_agents": (
            len(agents) == 4
            and len({agent.descriptor.context_isolation_key for agent in agents}) == 4
            and len({agent.private_memory_namespace for agent in agents}) == 4
        ),
        "formal_four_stage_protocol_completed": snapshot.stage == "CANDIDATE" and {
            "HYPOTHESIS_PROPOSAL",
            "ADVERSARIAL_REVIEW",
            "REPLICATION_REPORT",
            "BOUNDED_SYNTHESIS",
        }.issubset({message.message_type for message in snapshot.messages}),
        "kernel_retains_candidate_state": snapshot.candidate_state == "PENDING_EPISTEMIC_REVIEW",
        "all_provider_support_audits_pass": all(
            receipt is not None
            and receipt.status == "COMPLETED"
            and receipt.provider_audit.get("status", "").startswith("PASS_PROVIDER")
            for receipt in final_role_receipts
        ),
        "reviewer_falsifies_overbroad_claim": bool(reviewer)
        and reviewer.payload.get("recommended_epistemic_state") == "FALSIFIED",
        "replicator_independently_fails_overbroad_claim": bool(replicator)
        and replicator.payload.get("replication_outcome") == "FAILED",
        "synthesizer_preserves_bounded_local_rules": _canonical_rules(synth_claims) == EXPECTED_LOCAL_RULES,
        "deliberation_replay_valid": session.verify_replay()["valid"],
    }
    if coordinated:
        applied_coordination_refs = {
            receipt.message_ref
            for receipt in snapshot.coordination_receipts
            if receipt.status == "COMPLETED" and not receipt.errors
        }
        applied_coordination_proposals = [
            proposal
            for proposal in snapshot.coordination_proposals
            if f"coordination://{proposal.proposal_id}/{proposal.proposal_hash}" in applied_coordination_refs
        ]
        coordinator_identity_values = {
            coordinator.agent_id,
            coordinator.descriptor.context_isolation_key,
            coordinator.private_memory_namespace,
            coordinator.credit_subject_id,
        }
        role_identity_values = {
            value
            for agent in agents
            for value in (
                agent.agent_id,
                agent.descriptor.context_isolation_key,
                agent.private_memory_namespace,
                agent.credit_subject_id,
            )
        }
        gates.update(
            {
                "coordinator_identity_isolated": coordinator_identity_values.isdisjoint(role_identity_values),
                "coordinator_uses_public_formal_state": all(
                    receipt.context_hash and receipt.work_order_hash
                    for receipt in snapshot.coordination_receipts
                ),
                "kernel_applies_dynamic_route": bool(snapshot.coordination_proposals)
                and bool(applied_coordination_proposals)
                and applied_coordination_proposals[-1].route_action == "FINALIZE_CANDIDATE"
                and snapshot.candidate_state == "PENDING_EPISTEMIC_REVIEW",
                "coordination_provider_audits_pass": all(
                    receipt.provider_audit.get("status", "").startswith("PASS_PROVIDER")
                    for receipt in snapshot.coordination_receipts
                    if receipt.status == "COMPLETED"
                ),
                "minimal_coordination_protocol_completed": len(applied_coordination_proposals) == 5,
            }
        )
    result = {
        "smoke_id": (
            "life-cog3r-cognitive-coordination-v0-1"
            if coordinated
            else "life-cog3r-cognitive-agents-four-role-v0-2"
        ),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "created_at": _utc_now(),
        "source_project": "LIFE_COG3R",
        "gates": gates,
        "session_stage": snapshot.stage,
        "candidate_state": snapshot.candidate_state,
        "message_count": len(snapshot.messages),
        "execution_receipt_count": len(snapshot.execution_receipts),
        "coordination_proposal_count": len(snapshot.coordination_proposals),
        "coordination_receipt_count": len(snapshot.coordination_receipts),
        "recovered_blocked_execution_count": sum(
            receipt.status == "BLOCKED"
            for receipt in (*snapshot.execution_receipts, *snapshot.coordination_receipts)
        ),
        "provider_organizations": len(
            {
                agent.descriptor.provider_id
                for agent in (*agents, *((coordinator,) if coordinator else ()))
            }
        ),
        "replay": session.verify_replay(),
        "boundary": (
            "This smoke establishes a provider-backed four-role cognitive deliberation runtime"
            + (" with Kernel-gated cognitive coordination" if coordinated else "")
            + " over internal project evidence. It does not establish group superiority, production reliability, "
            "endogenous problem definition, or cognition ontology."
        ),
    }
    _write_json(output_dir / "smoke_result.json", result)
    manifest_files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest_files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    manifest = {"status": result["status"], "files": manifest_files}
    manifest["manifest_hash"] = _hash_bytes(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    _write_json(output_dir / "manifest.json", manifest)
    return result


def main() -> int:
    default_pack, default_gate = default_paths()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack", type=Path, default=default_pack)
    parser.add_argument("--gate-file", type=Path, default=default_gate)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "outputs" / f"cognitive_agents_smoke_{timestamp}",
    )
    parser.add_argument("--coordinated", action="store_true")
    args = parser.parse_args()
    try:
        result = run_smoke(
            args.source_pack,
            args.gate_file,
            args.output_dir,
            coordinated=args.coordinated,
        )
    except Exception as exc:
        failure = {
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "created_at": _utc_now(),
        }
        _write_json(args.output_dir.resolve() / "smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
