"""Live cognitive-team formation smoke over frozen LIFE-COG3R evidence."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE_ROOT.parent
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ARM_BEST_MEMBER,
    ARM_DYNAMIC_TEAM,
    ARM_FIXED_TEAM,
    AgentDescriptor,
    AgentRegistry,
    AgentRoleRequirement,
    CreditLedger,
    JsonlCreditEventStore,
    ProviderTaskRouter,
)
from agentos_runtime import CognitiveTeamFormationRuntime, DeliberationSeed  # noqa: E402
from examples.project_source_group_cognition_smoke import (  # noqa: E402
    LiveProviderSpec,
    OpenAICompatibleJsonAdapter,
    default_paths,
    load_source_dossier,
)


DEFAULT_PROBLEM_SNAPSHOT = CORE_ROOT / "examples" / "fixtures" / "life_cog3r_problem_seed_v0_1.json"
ROLE_CAPABILITIES = (
    ("HYPOTHESIS_GENERATOR", "hypothesis_generation"),
    ("ADVERSARIAL_REVIEWER", "adversarial_review"),
    ("REPLICATOR", "independent_replication"),
    ("SYNTHESIZER", "conflict_synthesis"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(encoded)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _seed_from_snapshot(snapshot: dict[str, Any], source_refs: tuple[str, ...]) -> DeliberationSeed:
    payload = snapshot["deliberation_seed"]
    evidence_refs = tuple(
        next(ref for ref in source_refs if ref.endswith(suffix))
        for suffix in (
            "#LIFE_COG3R_IndependentQA_v0_1.json",
            "#LIFE_COG3R_MachineVerdict_v0_1.json",
        )
    )
    return DeliberationSeed.create(
        seed_id=payload["seed_id"],
        source_problem_id=payload["source_problem_id"],
        objective=payload["objective"],
        research_object=payload["research_object"],
        project_scope=payload["project_scope"],
        evidence_refs=evidence_refs,
        rival_explanations=tuple(payload["rival_explanations"]),
        operationalization=payload["operationalization"],
        falsifier=payload["falsifier"],
        required_harnesses=tuple(payload["required_harnesses"]),
        unresolved_conflicts=tuple(payload["unresolved_conflicts"]),
        expected_cbit_gain=payload["expected_cbit_gain"],
        agenda_selection_receipt_ref=payload["agenda_selection_receipt_ref"],
    )


def _spec(provider: str, model: str, task_kind: str, max_tokens: int) -> LiveProviderSpec:
    if provider == "deepseek":
        return LiveProviderSpec(
            provider,
            model,
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            task_kind,
            max_tokens,
            {"thinking": {"type": "disabled"}},
        )
    return LiveProviderSpec(
        provider,
        model,
        "https://api.moonshot.cn/v1/chat/completions",
        "MOONSHOT_API_KEY",
        task_kind,
        max_tokens,
        {},
    )


def _descriptor(
    agent_id: str,
    role: str,
    capability: str,
    provider_id: str,
    model_id: str,
    scope: str,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=(capability, "source_grounded_json"),
        runner_id=f"runner-{agent_id}",
        harness_id="openai-compatible-http-json",
        provider_id=provider_id,
        model_id=model_id,
        context_isolation_key=f"private-context-{agent_id}",
        allowed_evidence_scopes=(scope,),
    )


def _arm_harness_summary(arm: str, arm_profile: dict[str, Any]) -> dict[str, Any]:
    mechanical = {
        ARM_BEST_MEMBER: {"observed_cbit_gain": 0.0, "normalized_cost": 0.10, "convergence_steps": 1},
        ARM_FIXED_TEAM: {"observed_cbit_gain": 0.0, "normalized_cost": 0.40, "convergence_steps": 4},
        ARM_DYNAMIC_TEAM: {"observed_cbit_gain": 0.0, "normalized_cost": 0.40, "convergence_steps": 4},
    }[arm]
    return {
        **mechanical,
        "errors_exposed": 0,
        "errors_corrected": 0,
        "negative_transfer_opportunities": 0,
        "negative_transfer_intercepts": 0,
        "measurement_boundary": (
            "Formation-readiness smoke only. No downstream research trial was executed, so observed_cbit_gain is "
            "mechanically frozen at zero for every arm."
        ),
    }


def _build_return_pack(output_dir: Path) -> Path:
    pack_path = output_dir / "AgentOS_CognitiveTeamFormation_LiveSmoke_ReturnPack_v0_1.zip"
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != pack_path and path.name != "manifest.json":
                archive.write(path, path.relative_to(output_dir).as_posix())
    return pack_path


def _write_manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    manifest = {"status": status, "files": files, "created_at": _utc_now()}
    manifest["manifest_hash"] = _hash_payload(manifest)
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def run_smoke(source_pack: Path, gate_file: Path, problem_snapshot: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads(problem_snapshot.read_text(encoding="utf-8"))
    dossier, source_inventory = load_source_dossier(source_pack, gate_file)
    seed = _seed_from_snapshot(snapshot, tuple(dossier["source_refs"]))
    _write_json(output_dir / "source_hash_inventory.json", source_inventory)

    evidence_payload = {
        "source_project": dossier["source_project"],
        "machine_verdict": dossier["machine_verdict"],
        "independent_structural_qa": dossier["independent_structural_qa"],
        "frozen_acceptance_gates": dossier["frozen_acceptance_gates"],
        "source_refs": list(seed.evidence_refs),
        "evidence_boundary": "Internal project evidence; negative results remain binding.",
    }

    baseline_specs = {
        "framer-deepseek": _spec(
            "deepseek", "deepseek-v4-pro", "independent_problem_baseline_generation", 3600
        ),
        "framer-moonshot": _spec(
            "moonshot", "kimi-k2.5", "independent_problem_baseline_generation", 4800
        ),
    }
    formation_spec = _spec("deepseek", "deepseek-v4-pro", "cognitive_team_formation_proposal", 3600)
    trial_spec = _spec("moonshot", "kimi-k2.5", "team_trial_semantic_assessment", 3600)

    registry = AgentRegistry()
    for agent_id, spec in baseline_specs.items():
        registry.register(
            _descriptor(agent_id, "PROBLEM_FRAMER", "independent_problem_framing", spec.provider_id, spec.model_id, seed.project_scope)
        )
    for index, (role, capability) in enumerate(ROLE_CAPABILITIES):
        registry.register(
            _descriptor(
                f"fixed-{index}-deepseek",
                role,
                capability,
                "deepseek",
                "deepseek-v4-pro",
                seed.project_scope,
            )
        )
        registry.register(
            _descriptor(
                f"dynamic-{index}-deepseek",
                role,
                capability,
                "deepseek",
                "deepseek-v4-pro",
                seed.project_scope,
            )
        )
        registry.register(
            _descriptor(
                f"dynamic-{index}-moonshot",
                role,
                capability,
                "moonshot",
                "kimi-k2.5",
                seed.project_scope,
            )
        )

    runtime = CognitiveTeamFormationRuntime(
        runtime_id="life-cog3r-team-formation-live-v0-1",
        seed=seed,
        registry=registry,
        baseline_agent_ids=tuple(baseline_specs),
        baseline_routers={
            agent_id: ProviderTaskRouter([OpenAICompatibleJsonAdapter(spec)])
            for agent_id, spec in baseline_specs.items()
        },
        formation_router=ProviderTaskRouter([OpenAICompatibleJsonAdapter(formation_spec)]),
        trial_assessment_router=ProviderTaskRouter([OpenAICompatibleJsonAdapter(trial_spec)]),
        required_roles=tuple(
            AgentRoleRequirement(role=role, required_capabilities=(capability,))
            for role, capability in ROLE_CAPABILITIES
        ),
        fixed_team_id="life-cog3r-fixed-team",
        fixed_team_agent_ids=tuple(f"fixed-{index}-deepseek" for index in range(4)),
        workspace_root=output_dir / "runtime_public",
        evidence_payload=evidence_payload,
        admitted_evidence_refs=seed.evidence_refs,
        advisory_credit_profiles={
            agent.agent_id: {"trust_score": 0.5, "confidence": 0.0, "advisory_only": True}
            for agent in registry.registered_agents()
        },
        minimum_provider_diversity=2,
    )

    baselines = runtime.generate_independent_baselines()
    proposal = runtime.propose_team(team_id="life-cog3r-dynamic-team")
    decision = runtime.authorize_team(
        kernel_authorization_ref="kernel://life-cog3r/team-formation/v0-1",
        budget={"max_provider_calls": 6, "max_team_members": 4, "max_iterations": 1},
    )

    best_member = max(baselines, key=lambda item: (item.expected_cbit_gain, item.receipt_hash))
    fixed_agents = tuple(f"fixed-{index}-deepseek" for index in range(4))
    arm_profiles = {
        ARM_BEST_MEMBER: {
            "problem_question": best_member.question,
            "agent_ids": [best_member.agent_id],
            "selection_rule": "maximum member-predicted expected_cbit_gain; not a quality verdict",
        },
        ARM_FIXED_TEAM: {
            "problem_question": seed.objective,
            "agent_ids": list(fixed_agents),
            "selection_rule": "fixed all-DeepSeek role-complete baseline",
        },
        ARM_DYNAMIC_TEAM: {
            "problem_question": seed.objective,
            "agent_ids": list(proposal.selected_agent_ids),
            "selection_rule": "provider-proposed, Kernel-authorized problem-fit team",
            "formation_rationale": proposal.formation_rationale,
        },
    }
    subjects = {
        ARM_BEST_MEMBER: (best_member.agent_id, (best_member.agent_id,)),
        ARM_FIXED_TEAM: ("life-cog3r-fixed-team", fixed_agents),
        ARM_DYNAMIC_TEAM: (proposal.team_id, proposal.selected_agent_ids),
    }
    observations = []
    for arm in (ARM_BEST_MEMBER, ARM_FIXED_TEAM, ARM_DYNAMIC_TEAM):
        subject_id, agent_ids = subjects[arm]
        observations.append(
            runtime.assess_trial_arm(
                trial_id="life-cog3r-formation-readiness-v0-1",
                arm=arm,
                subject_id=subject_id,
                agent_ids=agent_ids,
                harness_protocol_id="formation-readiness-counterfactual-v0-1",
                budget_hash=decision.budget_hash,
                harness_receipt_ref=f"harness://life-cog3r/formation-readiness/{arm.lower()}",
                harness_summary=_arm_harness_summary(arm, arm_profiles[arm]),
                semantic_artifact={
                    "problem_question": arm_profiles[arm]["problem_question"],
                    "formation_rationale": arm_profiles[arm].get("formation_rationale", ""),
                    "measurement_boundary": "formation readiness only; source identity withheld",
                },
            )
        )

    evaluation = runtime.evaluate_counterfactual(tuple(observations))
    credit_store = JsonlCreditEventStore(output_dir / "credit_events.jsonl")
    credit_ledger = CreditLedger(credit_store)
    feedback = runtime.apply_credit_feedback(credit_ledger)
    replay = runtime.verify_replay()
    selected_providers = {
        registry.get(agent_id).provider_id for agent_id in proposal.selected_agent_ids
    }
    gates = {
        "two_independent_problem_baselines": len(baselines) == 2
        and len({item.provider_id for item in baselines}) == 2
        and len({item.context_isolation_key for item in baselines}) == 2,
        "same_complete_evidence_surface": all(item.evidence_refs == seed.evidence_refs for item in baselines),
        "provider_backed_team_proposal": bool(proposal.provider_invocation_receipt.get("receipt_hash")),
        "kernel_authorized_registered_team": decision.execution_authorized
        and all(registry.get(agent_id).enabled for agent_id in proposal.selected_agent_ids),
        "provider_diversity_floor": len(selected_providers) >= 2,
        "three_provider_backed_arms": len(observations) == 3
        and all(item.semantic_assessment_receipt_ref.startswith("provider-receipt://") for item in observations),
        "counterfactual_frozen": evaluation.frozen and not evaluation.route_selection_authority,
        "separate_credit_subjects": credit_ledger.profile(best_member.agent_id).subject_kind == "agent"
        and credit_ledger.profile(proposal.team_id).subject_kind == "team",
        "replay_valid": replay["valid"],
    }
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": "life-cog3r-cognitive-team-formation-live-v0-1",
        "status": status,
        "created_at": _utc_now(),
        "source_problem_id": seed.source_problem_id,
        "baseline_receipts": [item.as_dict() for item in baselines],
        "team_proposal": proposal.as_dict(),
        "kernel_decision": decision.as_dict(),
        "trial_observations": [item.as_dict() for item in observations],
        "counterfactual_evaluation": evaluation.as_dict(),
        "credit_feedback": feedback.as_dict(),
        "credit_profiles": {
            best_member.agent_id: credit_ledger.profile(best_member.agent_id).as_dict(),
            proposal.team_id: credit_ledger.profile(proposal.team_id).as_dict(),
        },
        "replay_verification": replay,
        "gates": gates,
        "boundary": (
            "This smoke validates independent baseline generation, provider-supported team formation, Kernel authorization, "
            "equal-protocol formation-readiness comparison, and separate credit. It does not claim that the dynamic team "
            "improves project cognition; observed Cbit is zero because no downstream research trial was executed."
        ),
    }
    result["result_hash"] = _hash_payload(result)
    _write_json(output_dir / "smoke_result.json", result)
    _write_json(output_dir / "runtime_snapshot.json", runtime.snapshot().as_dict())
    _write_json(output_dir / "replay_verification.json", replay)
    _write_json(
        output_dir / "rollback_pointer.json",
        {
            "rollback_target": "pre-team-formation-state",
            "source_seed_hash": seed.seed_hash,
            "kernel_decision_hash": decision.decision_hash,
            "runtime_event_store": str(runtime.public_store_path),
            "created_at": _utc_now(),
        },
    )
    _write_json(
        output_dir / "cross_project_pointer_update_candidate.json",
        {
            "candidate_state": "CANDIDATE_ONLY",
            "feature": "cognitive_team_formation_runtime_v0_1",
            "smoke_result_hash": result["result_hash"],
            "promotion_authorized": False,
            "boundary": result["boundary"],
        },
    )
    _build_return_pack(output_dir)
    _write_manifest(output_dir, status)
    return result


def main() -> int:
    default_pack, default_gate = default_paths()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack", type=Path, default=default_pack)
    parser.add_argument("--gate-file", type=Path, default=default_gate)
    parser.add_argument("--problem-snapshot", type=Path, default=DEFAULT_PROBLEM_SNAPSHOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "outputs" / f"cognitive_team_formation_smoke_{timestamp}",
    )
    args = parser.parse_args()
    try:
        result = run_smoke(args.source_pack, args.gate_file, args.problem_snapshot, args.output_dir)
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
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_dir": str(args.output_dir.resolve()),
                "gates": result["gates"],
                "verdict_vs_best_member": result["counterfactual_evaluation"]["verdict_vs_best_member"],
                "verdict_vs_fixed_team": result["counterfactual_evaluation"]["verdict_vs_fixed_team"],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
