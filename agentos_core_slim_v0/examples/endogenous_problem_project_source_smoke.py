"""Live group problem-definition smoke over the LIFE-COG3R project source."""

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
    EndogenousProblemRuntime,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)
from examples.cognitive_agents_project_source_smoke import (  # noqa: E402
    _coordinator_spec,
    _provider_specs as _core_provider_specs,
)
from examples.project_source_group_cognition_smoke import (  # noqa: E402
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


def _problem_provider_specs() -> dict[str, LiveProviderSpec]:
    return {
        "PROBLEM_FRAMER": LiveProviderSpec(
            "deepseek",
            "deepseek-v4-flash",
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            "endogenous_problem_framing",
            4500,
            {"thinking": {"type": "disabled"}},
        ),
        "PROBLEM_CRITIC": LiveProviderSpec(
            "moonshot",
            "kimi-k2.5",
            "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY",
            "problem_candidate_adversarial_review",
            5500,
            {},
        ),
        "RESEARCHABILITY_ASSESSOR": LiveProviderSpec(
            "deepseek",
            "deepseek-v4-pro",
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            "problem_researchability_assessment",
            4500,
            {"thinking": {"type": "disabled"}},
        ),
        "AGENDA_SYNTHESIZER": LiveProviderSpec(
            "moonshot",
            "kimi-k2.5",
            "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY",
            "group_agenda_synthesis_and_selection",
            4500,
            {},
        ),
    }


def _agent(role: str, index: int, spec: LiveProviderSpec, scope: str, prefix: str) -> CognitiveAgent:
    descriptor = AgentDescriptor(
        agent_id=f"{prefix}-{role.lower().replace('_', '-')}-{spec.model_id}",
        role=role,
        capabilities=("semantic_judgment", "source_read", "formal_receipt_write"),
        runner_id=f"{prefix}-runner-{index}",
        harness_id=f"{prefix}-harness-{index}",
        provider_id=spec.provider_id,
        context_isolation_key=f"{prefix}-{role.lower()}-context",
        allowed_evidence_scopes=(scope,),
    )
    return CognitiveAgent(
        descriptor,
        standard_role_contract(role),
        model_id=spec.model_id,
        private_memory_namespace=f"{prefix}-{role.lower()}-memory",
        harness_capabilities=("source_read", "formal_receipt_write"),
        credit_subject_id=f"credit-{descriptor.agent_id}",
    )


def _provider_adapter(agent: CognitiveAgent, spec: LiveProviderSpec, adapter_id: str) -> ProviderCognitiveAgentAdapter:
    return ProviderCognitiveAgentAdapter(
        adapter_id,
        ProviderTaskRouter([OpenAICompatibleJsonAdapter(spec), OpenAICompatibleJsonAdapter(spec)]),
    )


def run_smoke(source_pack: Path, gate_file: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dossier, source_inventory = load_source_dossier(source_pack, gate_file)
    _write_json(output_dir / "source_hash_inventory.json", source_inventory)
    source_refs = tuple(dossier["source_refs"])
    scope = "project://LIFE_COG3R"
    discovery_objective = (
        "Discover the next high-value falsifiable research question from the admitted unresolved project evidence. "
        "No candidate research question is seeded; derive a plural problem set before criticism and selection."
    )
    evidence_payload = {
        "source_project": dossier["source_project"],
        "evidence_coordinate": dossier["evidence_coordinate"],
        "frozen_acceptance_gates": dossier["frozen_acceptance_gates"],
        "machine_verdict": dossier["machine_verdict"],
        "independent_structural_qa": dossier["independent_structural_qa"],
        "source_refs": dossier["source_refs"],
        "seeded_problem_questions": [],
    }
    _write_json(
        output_dir / "problem_input_contract.json",
        {
            "discovery_objective": discovery_objective,
            "seeded_problem_questions": [],
            "evidence_refs": list(source_refs),
            "scope": scope,
        },
    )

    specs = _problem_provider_specs()
    problem_agents: list[CognitiveAgent] = []
    problem_adapters = {}
    for index, (role, spec) in enumerate(specs.items(), start=1):
        agent = _agent(role, index, spec, scope, "life-cog3r-problem")
        problem_agents.append(agent)
        problem_adapters[agent.agent_id] = _provider_adapter(
            agent,
            spec,
            f"live-problem-{role.lower()}-adapter",
        )

    problem_runtime = EndogenousProblemRuntime(
        session_id="life-cog3r-endogenous-problem-live",
        discovery_objective=discovery_objective,
        project_scope=scope,
        evidence_refs=source_refs,
        evidence_payload=evidence_payload,
        agents=tuple(problem_agents),
        adapters=problem_adapters,
        workspace_root=output_dir / "problem_private_workspaces",
        kernel_authorization_ref="kernel-authorization://life-cog3r-problem-definition",
        minimum_priority=0.2,
    )
    problem_snapshot = problem_runtime.run_to_candidate(max_retries_per_stage=2)
    _write_json(output_dir / "problem_definition_snapshot.json", problem_snapshot.as_dict())
    _write_json(
        output_dir / "problem_team.json",
        {"agents": [agent.as_dict() for agent in problem_agents]},
    )

    coordination_snapshot = None
    coordination_session = None
    coordinator = None
    if problem_snapshot.deliberation_seed is not None:
        core_specs = _core_provider_specs()
        core_agents: list[CognitiveAgent] = []
        core_adapters = {}
        for index, (role, spec) in enumerate(core_specs.items(), start=1):
            agent = _agent(role, index, spec, scope, "life-cog3r-seeded")
            core_agents.append(agent)
            core_adapters[agent.agent_id] = _provider_adapter(
                agent,
                spec,
                f"live-seeded-{role.lower()}-adapter",
            )
        coordinator_spec = _coordinator_spec()
        coordinator = _agent("COORDINATOR", 5, coordinator_spec, scope, "life-cog3r-seeded")
        coordination_runtime = CognitiveCoordinationRuntime(
            coordinator=coordinator,
            adapter=_provider_adapter(coordinator, coordinator_spec, "live-seeded-coordinator-adapter"),
            workspace_root=output_dir / "seeded_coordinator_private_workspace",
            max_cycles=4,
            max_role_executions_per_role=2,
        )
        coordination_session = CognitiveDeliberationSession.from_deliberation_seed(
            seed=problem_snapshot.deliberation_seed,
            session_id="life-cog3r-emergent-problem-coordination-intake",
            frozen_gate_refs=(str(gate_file.resolve()),),
            agents=tuple(core_agents),
            adapters=core_adapters,
            workspace_root=output_dir / "seeded_role_private_workspaces",
            kernel_authorization_ref="kernel-authorization://life-cog3r-emergent-problem-intake",
            coordination_runtime=coordination_runtime,
        )
        coordination_snapshot = coordination_session.execute_current()
        retries = 0
        while coordination_snapshot.stage == "BLOCKED" and retries < 2:
            coordination_snapshot = coordination_session.retry_blocked()
            retries += 1
        _write_json(output_dir / "coordination_intake_snapshot.json", coordination_snapshot.as_dict())
        _write_json(
            output_dir / "coordination_intake_team.json",
            {
                "coordinator": coordinator.as_dict(),
                "role_agents": [agent.as_dict() for agent in core_agents],
            },
        )

    message_by_type = {message.message_type: message for message in problem_snapshot.messages}
    candidate_payload = message_by_type.get("PROBLEM_CANDIDATE_SET")
    critique_payload = message_by_type.get("PROBLEM_CRITIQUE")
    researchability_payload = message_by_type.get("RESEARCHABILITY_REPORT")
    selection_payload = message_by_type.get("AGENDA_SELECTION_PROPOSAL")
    candidates = candidate_payload.payload.get("problem_candidates", []) if candidate_payload else []
    generated_ids = {str(candidate.get("problem_id")) for candidate in candidates}
    selected_id = (
        str(selection_payload.payload.get("selected_problem_id", ""))
        if selection_payload
        else ""
    )
    surviving_ids = set(critique_payload.payload.get("surviving_problem_ids", [])) if critique_payload else set()
    researchable_ids = (
        set(researchability_payload.payload.get("researchable_problem_ids", []))
        if researchability_payload
        else set()
    )
    role_receipts = {}
    for receipt in problem_snapshot.execution_receipts:
        role_receipts[receipt.stage] = receipt
    gates = {
        "no_problem_question_seeded": evidence_payload["seeded_problem_questions"] == [],
        "plural_problem_candidates_emerged": len(candidates) >= 2 and len(generated_ids) == len(candidates),
        "selected_problem_was_internally_generated": bool(selected_id) and selected_id in generated_ids,
        "selected_problem_survived_group_challenge": selected_id in surviving_ids,
        "selected_problem_is_independently_researchable": selected_id in researchable_ids,
        "critic_and_assessor_information_isolated": bool(critique_payload)
        and bool(researchability_payload)
        and critique_payload.parent_message_refs == researchability_payload.parent_message_refs
        and len(critique_payload.parent_message_refs) == 1,
        "all_problem_provider_audits_pass": all(
            receipt is not None
            and receipt.status == "COMPLETED"
            and receipt.provider_audit.get("status", "").startswith("PASS_PROVIDER")
            for receipt in (
                role_receipts.get("PROBLEM_FRAMING"),
                role_receipts.get("PROBLEM_REVIEW"),
                role_receipts.get("RESEARCHABILITY"),
                role_receipts.get("AGENDA_SYNTHESIS"),
            )
        ),
        "kernel_retains_pending_agenda_state": problem_snapshot.candidate_state == "PENDING_AGENDA_REVIEW"
        and problem_snapshot.deliberation_seed is not None
        and problem_snapshot.deliberation_seed.execution_authorized is False,
        "problem_replay_valid": problem_runtime.verify_replay()["valid"],
        "seed_enters_live_coordination_intake": coordination_snapshot is not None
        and coordination_snapshot.stage == "GENERATION"
        and coordination_session.objective == problem_snapshot.deliberation_seed.objective,
        "coordinator_does_not_form_final_state": coordination_snapshot is not None
        and coordination_snapshot.candidate_state == "NOT_FORMED",
        "coordination_intake_replay_valid": coordination_session is not None
        and coordination_session.verify_replay()["valid"],
    }
    result = {
        "smoke_id": "life-cog3r-endogenous-problem-runtime-v0-1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "created_at": _utc_now(),
        "source_project": "LIFE_COG3R",
        "gates": gates,
        "problem_stage": problem_snapshot.stage,
        "problem_candidate_state": problem_snapshot.candidate_state,
        "generated_problem_count": len(candidates),
        "selected_problem_id": selected_id,
        "selected_question": (
            problem_snapshot.deliberation_seed.objective
            if problem_snapshot.deliberation_seed
            else ""
        ),
        "problem_execution_receipt_count": len(problem_snapshot.execution_receipts),
        "problem_recovered_block_count": sum(
            receipt.status == "BLOCKED" for receipt in problem_snapshot.execution_receipts
        ),
        "coordination_intake_stage": coordination_snapshot.stage if coordination_snapshot else "NOT_RUN",
        "problem_replay": problem_runtime.verify_replay(),
        "coordination_replay": coordination_session.verify_replay() if coordination_session else {},
        "boundary": (
            "This smoke establishes provider-backed plural problem framing, independent criticism and researchability "
            "assessment, Kernel-gated pending agenda selection, and live coordination intake. It does not establish "
            "problem quality superiority, automatic execution authority, or production autonomous science."
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
        default=REPO_ROOT / "outputs" / f"endogenous_problem_smoke_{timestamp}",
    )
    args = parser.parse_args()
    try:
        result = run_smoke(args.source_pack, args.gate_file, args.output_dir)
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
