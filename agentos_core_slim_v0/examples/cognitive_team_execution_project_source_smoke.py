"""Three-arm cognitive-team execution smoke over frozen project sources."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable


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
    FrozenFindingTrialHarness,
    JsonlCreditEventStore,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    TrialFindingCatalogEntry,
    TrialFindingTruth,
)
from agentos_runtime import (  # noqa: E402
    AgentAdapterResult,
    CognitiveAgent,
    CognitiveCoordinationRuntime,
    CognitiveExecutionTrialSpec,
    CognitiveTeamExecutionRuntime,
    CognitiveTeamFormationRuntime,
    DeliberationSeed,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)
from examples.project_source_group_cognition_smoke import (  # noqa: E402
    LiveProviderSpec,
    OpenAICompatibleJsonAdapter,
    PORTABLE_SOURCE_ROOT,
    default_paths,
    load_source_dossier,
)


ROLES = (
    ("HYPOTHESIS_GENERATOR", "hypothesis_generation"),
    ("ADVERSARIAL_REVIEWER", "adversarial_review"),
    ("REPLICATOR", "independent_replication"),
    ("SYNTHESIZER", "conflict_synthesis"),
)
HIDDEN_KEYS = {"expected_state", "ground_truth", "trial_truth", "truths"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_payload(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(data)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _contains_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in forbidden for key in value):
            return True
        return any(_contains_key(item, forbidden) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, forbidden) for item in value)
    return False


@dataclass(frozen=True)
class ProjectTrialCase:
    case_id: str
    scope: str
    objective: str
    evidence_refs: tuple[str, ...]
    evidence_payload: dict[str, Any]
    finding_catalog: tuple[TrialFindingCatalogEntry, ...]
    hidden_truths: tuple[TrialFindingTruth, ...]
    source_inventory: tuple[dict[str, Any], ...]


def _inventory(paths: tuple[Path, ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": _hash_bytes(path.read_bytes())}
        for path in paths
    )


def load_life_case() -> ProjectTrialCase:
    pack, gate = default_paths()
    dossier, inventory = load_source_dossier(pack, gate)
    refs = tuple(dossier["source_refs"])
    return ProjectTrialCase(
        case_id="life-cog3r",
        scope="project://LIFE_COG3R",
        objective=(
            "Classify the bounded LIFE_COG3R findings from frozen internal evidence without promoting local G4 "
            "observations into overall retention, causality, aligned-Cbit, or ontology claims."
        ),
        evidence_refs=refs,
        evidence_payload={
            "source_project": dossier["source_project"],
            "machine_verdict": dossier["machine_verdict"],
            "independent_structural_qa": dossier["independent_structural_qa"],
            "frozen_acceptance_gates": dossier["frozen_acceptance_gates"],
            "source_refs": list(refs),
        },
        finding_catalog=(
            TrialFindingCatalogEntry("LIFE-F1", "The frozen machine classification is FAIL_NEGATIVE_CONTROLS."),
            TrialFindingCatalogEntry("LIFE-F2", "The evidence supports overall validation-gated retention."),
            TrialFindingCatalogEntry(
                "LIFE-F3", "Whether the local G4 observations generalize beyond the recorded rules remains unresolved."
            ),
        ),
        hidden_truths=(
            TrialFindingTruth("LIFE-F1", "SUPPORTED"),
            TrialFindingTruth("LIFE-F2", "REJECTED"),
            TrialFindingTruth("LIFE-F3", "UNRESOLVED"),
        ),
        source_inventory=tuple(inventory),
    )


def load_math_cbit1_case() -> ProjectTrialCase:
    fixture_path = PORTABLE_SOURCE_ROOT / "math_cbit1_source_v0_1.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    config = fixture["frozen_config"]
    retention = fixture["retention_score_audit"]
    holdout = fixture["chronological_holdout_rows"]
    if config.get("frozen_before_late_evaluation") is not True:
        raise ValueError("math_cbit1_config_not_frozen")
    if float(holdout["compression"]["permutation_p"]) <= 0.05:
        raise ValueError("math_cbit1_fixture_compression_null_changed")
    if float(holdout["full"]["permutation_p"]) >= 0.05:
        raise ValueError("math_cbit1_fixture_full_signal_changed")
    refs = tuple(f"{fixture_path.resolve()}#{section}" for section in (
        "frozen_config",
        "retention_score_audit",
        "chronological_holdout_rows",
    ))
    return ProjectTrialCase(
        case_id="math-cbit1",
        scope="project://MATH_CBIT1",
        objective=(
            "Classify the frozen MATH_CBIT1 retention and chronological holdout findings while separating "
            "compression-only evidence from the full registered feature result."
        ),
        evidence_refs=refs,
        evidence_payload={
            "source_project": "MATH_CBIT1",
            "frozen_config": config,
            "retention_score_audit": retention,
            "chronological_holdout_rows": holdout,
            "source_refs": list(refs),
        },
        finding_catalog=(
            TrialFindingCatalogEntry("MATH-F1", "The retention score configuration was frozen before late evaluation."),
            TrialFindingCatalogEntry(
                "MATH-F2", "Compression-only features add a significant chronological Spearman gain over baseline."
            ),
            TrialFindingCatalogEntry(
                "MATH-F3", "Whether the registered signal transfers beyond this corpus remains unresolved."
            ),
        ),
        hidden_truths=(
            TrialFindingTruth("MATH-F1", "SUPPORTED"),
            TrialFindingTruth("MATH-F2", "REJECTED"),
            TrialFindingTruth("MATH-F3", "UNRESOLVED"),
        ),
        source_inventory=_inventory((fixture_path,)),
    )


def load_ocs1r2_case() -> ProjectTrialCase:
    fixture_path = PORTABLE_SOURCE_ROOT / "ocs1r2_source_v0_1.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    plan_text = fixture["analysis_freeze_source"]
    qa_text = fixture["qa_contract_source"]
    preflight_text = fixture["preflight_source"]
    for label, source in (
        ("analysis_freeze", plan_text),
        ("qa_contract", qa_text),
        ("preflight", preflight_text),
    ):
        compile(source, f"{fixture_path}#{label}", "exec")
    if "before any complete model outcome table existed" not in plan_text:
        raise ValueError("ocs1r2_analysis_freeze_boundary_missing")
    if '"hidden_stop_rule": "Run only if R2.1-R2.5 all pass."' not in plan_text:
        raise ValueError("ocs1r2_hidden_stop_rule_missing")
    refs = tuple(f"{fixture_path.resolve()}#{section}" for section in (
        "analysis_freeze_source",
        "qa_contract_source",
        "preflight_source",
    ))
    return ProjectTrialCase(
        case_id="ocs1r2",
        scope="project://OCS1R2",
        objective=(
            "Classify what the frozen OCS1R2 analysis and QA source contracts establish before outcome artifacts "
            "are admitted; preserve the hidden-probe stop rule."
        ),
        evidence_refs=refs,
        evidence_payload={
            "source_project": "OCS1R2",
            "analysis_freeze_source": plan_text,
            "qa_contract_source": qa_text,
            "source_refs": list(refs),
        },
        finding_catalog=(
            TrialFindingCatalogEntry(
                "OCS-F1", "The analysis thresholds were frozen before any complete model outcome table existed."
            ),
            TrialFindingCatalogEntry("OCS-F2", "The source contracts alone establish that R2.1 through R2.5 passed."),
            TrialFindingCatalogEntry(
                "OCS-F3", "Whether the hidden probe may run remains unresolved until all R2.1-R2.5 gates pass."
            ),
        ),
        hidden_truths=(
            TrialFindingTruth("OCS-F1", "SUPPORTED"),
            TrialFindingTruth("OCS-F2", "REJECTED"),
            TrialFindingTruth("OCS-F3", "UNRESOLVED"),
        ),
        source_inventory=_inventory((fixture_path,)),
    )


class RecordingProvider:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.profile = delegate.profile
        self.tasks: list[Any] = []

    def invoke(self, task: Any) -> dict[str, Any]:
        self.tasks.append(task)
        return self.delegate.invoke(task)


class StaticProvider:
    def __init__(
        self,
        provider_id: str,
        model_id: str,
        task_kinds: tuple[str, ...],
        result_factory: Callable[[Any], dict[str, Any]],
    ) -> None:
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=model_id,
            task_kinds=task_kinds,
            max_timeout_seconds=120,
        )
        self.result_factory = result_factory

    def invoke(self, task: Any) -> dict[str, Any]:
        return {
            "result": self.result_factory(task),
            "usage": {"total_tokens": 1},
            "provenance_refs": list(task.allowed_evidence),
        }


class ScriptedRoleAdapter:
    def __init__(self, descriptor: AgentDescriptor) -> None:
        self.adapter_id = f"scripted-role-{descriptor.agent_id}"
        self.descriptor = descriptor

    def invoke(self, cognitive_agent: Any, work_order: Any, context_view: Any, private_workspace: Any) -> Any:
        refs = list(work_order.allowed_evidence_refs)
        role = cognitive_agent.role
        if role == "HYPOTHESIS_GENERATOR":
            payload = {
                "hypotheses": ["The broad promotion may exceed the frozen evidence."],
                "assumptions": ["Source hashes and frozen gates are binding."],
                "rival_explanations": ["A scope-local signal may explain the result."],
                "falsifiable_predictions": ["The held-out Harness rejects at least one broad finding."],
                "evidence_refs": refs,
                "confidence": 0.7,
            }
        elif role == "ADVERSARIAL_REVIEWER":
            payload = {
                "objections": ["Do not promote an absent or non-significant result."],
                "strongest_falsifier": "A frozen negative or stop gate remains binding.",
                "rival_set_coverage": 0.8,
                "evidence_refs": refs,
                "recommended_epistemic_state": "PENDING",
                "confidence": 0.8,
            }
        elif role == "REPLICATOR":
            payload = {
                "replication_outcome": "INCONCLUSIVE",
                "gate_results": {"source_contract_replayed": True},
                "deviations": ["No new execution is inferred from source-only evidence."],
                "evidence_refs": refs,
                "confidence": 0.75,
            }
        else:
            payload = {
                "converged_claims": ["Only bounded source-backed findings survive."],
                "unresolved_conflicts": ["Cross-scope transfer remains unresolved."],
                "minority_positions": ["A broader result would require new evidence."],
                "evidence_refs": refs,
                "uncertainties": ["No outcome is promoted beyond the frozen coordinate."],
            }
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.descriptor.provider_id,
            model_id=self.descriptor.model_id,
            invocation_receipt_ref=f"fixture-provider://{work_order.work_order_id}",
        )


class ScriptedCoordinatorAdapter:
    def __init__(self, coordinator: CognitiveAgent) -> None:
        self.adapter_id = f"scripted-coordinator-{coordinator.agent_id}"
        self.coordinator = coordinator
        self.index = 0

    def invoke(self, cognitive_agent: Any, work_order: Any, context_view: Any, private_workspace: Any) -> Any:
        sequence = (
            ("RUN_ROLE", "HYPOTHESIS_GENERATOR"),
            ("RUN_ROLE", "ADVERSARIAL_REVIEWER"),
            ("RUN_ROLE", "REPLICATOR"),
            ("PROCEED_TO_SYNTHESIS", "SYNTHESIZER"),
            ("FINALIZE_CANDIDATE", "NONE"),
        )
        action, target = sequence[self.index]
        self.index += 1
        payload = {
            "route_action": action,
            "target_role": target,
            "rationale": "Apply the same bounded protocol to both team arms.",
            "unresolved_questions": ["Which public findings survive?"],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": list(work_order.allowed_evidence_refs),
            "expected_cbit_gain": 0.4,
            "stop_condition": "Stop after bounded synthesis.",
        }
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.coordinator.descriptor.provider_id,
            model_id=self.coordinator.model_id,
            invocation_receipt_ref=f"fixture-provider://{work_order.work_order_id}",
        )


def _live_spec(provider: str, model: str, task_kind: str, max_tokens: int) -> LiveProviderSpec:
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
    case: ProjectTrialCase,
    agent_id: str,
    role: str,
    capability: str,
    provider_id: str,
    model_id: str,
) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=(capability, "source_read", "source_grounded_json"),
        runner_id=f"runner-{agent_id}",
        harness_id="cognitive-team-execution-project-source-harness",
        provider_id=provider_id,
        model_id=model_id,
        context_isolation_key=f"{case.case_id}-context-{agent_id}",
        allowed_evidence_scopes=(case.scope,),
    )


def _candidate(case: ProjectTrialCase, mode: str) -> dict[str, Any]:
    by_state = {item.expected_state: item.finding_id for item in case.hidden_truths}
    if mode == "correct":
        supported = [by_state["SUPPORTED"]]
        rejected = [by_state["REJECTED"]]
        unresolved = [by_state["UNRESOLVED"]]
    elif mode == "partial":
        supported = [by_state["SUPPORTED"], by_state["UNRESOLVED"]]
        rejected = [by_state["REJECTED"]]
        unresolved = []
    else:
        supported = [item.finding_id for item in case.finding_catalog]
        rejected = []
        unresolved = []
    return {
        "answer": f"Fixture-controlled bounded classification: {mode}.",
        "supported_finding_ids": supported,
        "rejected_finding_ids": rejected,
        "unresolved_finding_ids": unresolved,
        "rival_explanations": ["A broader conclusion would require another evidence coordinate."],
        "falsifier": "A source-backed finding or frozen gate contradicts this classification.",
        "evidence_refs": list(case.evidence_refs),
        "uncertainties": ["Cross-scope transfer is not established."],
    }


def _baseline_result(case: ProjectTrialCase, label: str) -> Callable[[Any], dict[str, Any]]:
    def result(task: Any) -> dict[str, Any]:
        return {
            "problem_id": f"{case.case_id}-{label}-{task.inputs['blind_member_id']}",
            "question": f"{case.objective} Independent baseline {label}: which finding is most fragile?",
            "research_object": "bounded_project_finding_classification",
            "scope": case.scope,
            "triggering_anomaly": "The broad claim may exceed frozen source evidence.",
            "rival_explanations": ["scope-local effect", "unsupported promotion"],
            "falsifier": "The held-out Harness contradicts the classification.",
            "required_harnesses": ["frozen-finding-trial-harness"],
            "expected_cbit_gain": 0.6,
            "evidence_refs": list(case.evidence_refs),
        }

    return result


def _formation_result(case: ProjectTrialCase, provider_mode: str) -> Callable[[Any], dict[str, Any]]:
    def result(task: Any) -> dict[str, Any]:
        return {
            "selected_agent_ids": [f"dynamic-{index}" for index in range(4)],
            "role_coverage": {role: f"dynamic-{index}" for index, (role, _) in enumerate(ROLES)},
            "formation_rationale": (
                "Use a role-complete, context-isolated team; live mode keeps one provider organization after an "
                "independently recorded Moonshot availability failure."
                if provider_mode == "live"
                else "Use a role-complete, context-isolated, two-provider fixture team."
            ),
            "expected_cbit_gain": 0.7,
            "independence_risks": ["Two provider families are reused across roles."],
            "negative_transfer_risks": ["The source coordinate may not transfer."],
            "evidence_refs": list(case.evidence_refs),
        }

    return result


def _assessment_result(case: ProjectTrialCase) -> Callable[[Any], dict[str, Any]]:
    def result(task: Any) -> dict[str, Any]:
        mechanical = task.inputs["harness_owned_metrics"]
        return {
            "blind_arm_id": task.inputs["blind_arm_id"],
            "quality_score": mechanical["observed_cbit_gain"],
            **mechanical,
            "evidence_refs": list(case.evidence_refs),
        }

    return result


def _recording_static(
    recordings: list[RecordingProvider],
    provider_id: str,
    model_id: str,
    task_kind: str,
    result_factory: Callable[[Any], dict[str, Any]],
) -> RecordingProvider:
    adapter = RecordingProvider(StaticProvider(provider_id, model_id, (task_kind,), result_factory))
    recordings.append(adapter)
    return adapter


def _recording_live(
    recordings: list[RecordingProvider],
    provider: str,
    model: str,
    task_kind: str,
    max_tokens: int,
) -> RecordingProvider:
    adapter = RecordingProvider(OpenAICompatibleJsonAdapter(_live_spec(provider, model, task_kind, max_tokens)))
    recordings.append(adapter)
    return adapter


def _build_runtime(
    case: ProjectTrialCase,
    output_dir: Path,
    provider_mode: str,
    coordinated: bool,
) -> tuple[CognitiveTeamExecutionRuntime, list[RecordingProvider]]:
    recordings: list[RecordingProvider] = []
    registry = AgentRegistry()
    registry.register(_descriptor(case, "framer-deepseek", "PROBLEM_FRAMER", "frame", "deepseek", "deepseek-v4-pro"))
    registry.register(_descriptor(case, "framer-moonshot", "PROBLEM_FRAMER", "frame", "moonshot", "kimi-k2.5"))
    for index, (role, capability) in enumerate(ROLES):
        registry.register(_descriptor(case, f"fixed-{index}", role, capability, "deepseek", "deepseek-v4-pro"))
        if provider_mode == "live":
            provider, model = "deepseek", ("deepseek-v4-flash" if index % 2 == 0 else "deepseek-v4-pro")
        else:
            provider, model = (("deepseek", "deepseek-v4-pro") if index % 2 == 0 else ("moonshot", "kimi-k2.5"))
        registry.register(_descriptor(case, f"dynamic-{index}", role, capability, provider, model))

    seed = DeliberationSeed.create(
        seed_id=f"{case.case_id}-execution-seed",
        source_problem_id=f"{case.case_id}-bounded-findings",
        objective=case.objective,
        research_object="bounded_project_finding_classification",
        project_scope=case.scope,
        evidence_refs=case.evidence_refs,
        rival_explanations=("scope-local effect", "unsupported broad promotion"),
        operationalization="Classify each public finding exactly once under the frozen source coordinate.",
        falsifier="The held-out finding Harness contradicts the candidate classification.",
        required_harnesses=("frozen-finding-trial-harness",),
        unresolved_conflicts=("Cross-scope transfer remains open.",),
        expected_cbit_gain=0.7,
        agenda_selection_receipt_ref=f"agenda://{case.case_id}/execution",
    )
    baseline_routers = {
        "framer-deepseek": ProviderTaskRouter(
            [_recording_static(recordings, "deepseek", "deepseek-v4-pro", "independent_problem_baseline_generation", _baseline_result(case, "a"))]
        ),
        "framer-moonshot": ProviderTaskRouter(
            [_recording_static(recordings, "moonshot", "kimi-k2.5", "independent_problem_baseline_generation", _baseline_result(case, "b"))]
        ),
    }
    formation_router = ProviderTaskRouter(
        [_recording_static(recordings, "formation-provider", "formation-model", "cognitive_team_formation_proposal", _formation_result(case, provider_mode))]
    )
    if provider_mode == "live":
        assessment_adapter = _recording_live(
            recordings, "deepseek", "deepseek-v4-pro", "team_trial_semantic_assessment", 2400
        )
    else:
        assessment_adapter = _recording_static(
            recordings, "assessment-provider", "assessment-model", "team_trial_semantic_assessment", _assessment_result(case)
        )
    formation = CognitiveTeamFormationRuntime(
        runtime_id=f"{case.case_id}-execution-formation",
        seed=seed,
        registry=registry,
        baseline_agent_ids=("framer-deepseek", "framer-moonshot"),
        baseline_routers=baseline_routers,
        formation_router=formation_router,
        trial_assessment_router=ProviderTaskRouter([assessment_adapter]),
        required_roles=tuple(AgentRoleRequirement(role, (capability,)) for role, capability in ROLES),
        fixed_team_id=f"{case.case_id}-fixed-team",
        fixed_team_agent_ids=tuple(f"fixed-{index}" for index in range(4)),
        workspace_root=output_dir / "formation-runtime",
        evidence_payload=case.evidence_payload,
        admitted_evidence_refs=case.evidence_refs,
        minimum_provider_diversity=1 if provider_mode == "live" else 2,
    )
    formation.generate_independent_baselines()
    formation.propose_team(team_id=f"{case.case_id}-dynamic-team")
    budget = {"max_provider_calls_per_arm": 20, "max_retries_per_stage": 1}
    decision = formation.authorize_team(
        kernel_authorization_ref=f"kernel://{case.case_id}/cognitive-team-execution",
        budget=budget,
    )

    team_adapters: dict[str, Any] = {}
    for agent_id in (*(f"fixed-{index}" for index in range(4)), *(f"dynamic-{index}" for index in range(4))):
        descriptor = registry.get(agent_id)
        if provider_mode == "live":
            adapter = _recording_live(
                recordings,
                descriptor.provider_id,
                descriptor.model_id,
                standard_role_contract(descriptor.role).provider_operation_id,
                3200,
            )
            team_adapters[agent_id] = ProviderCognitiveAgentAdapter(
                f"live-role-{case.case_id}-{agent_id}", ProviderTaskRouter([adapter])
            )
        else:
            team_adapters[agent_id] = ScriptedRoleAdapter(descriptor)

    if provider_mode == "live":
        solo_adapter = _recording_live(recordings, "deepseek", "deepseek-v4-pro", "solo_cognitive_trial", 2800)
        fixed_norm = _recording_live(
            recordings, "deepseek", "deepseek-v4-pro", "team_trial_output_normalization", 2800
        )
        dynamic_synthesizer = registry.get("dynamic-3")
        dynamic_norm = _recording_live(
            recordings,
            dynamic_synthesizer.provider_id,
            dynamic_synthesizer.model_id,
            "team_trial_output_normalization",
            3200,
        )
    else:
        solo_adapter = _recording_static(
            recordings, "deepseek", "deepseek-v4-pro", "solo_cognitive_trial", lambda task: _candidate(case, "partial")
        )
        fixed_norm = _recording_static(
            recordings,
            registry.get("fixed-3").provider_id,
            registry.get("fixed-3").model_id,
            "team_trial_output_normalization",
            lambda task: _candidate(case, "wrong"),
        )
        dynamic_norm = _recording_static(
            recordings,
            registry.get("dynamic-3").provider_id,
            registry.get("dynamic-3").model_id,
            "team_trial_output_normalization",
            lambda task: _candidate(case, "correct"),
        )

    def coordinator_factory(arm: str, workspace_root: Path) -> CognitiveCoordinationRuntime:
        descriptor = _descriptor(
            case,
            f"coordinator-{arm.lower()}",
            "COORDINATOR",
            "route_proposal",
            "deepseek",
            "deepseek-v4-flash",
        )
        coordinator = CognitiveAgent(
            descriptor,
            standard_role_contract("COORDINATOR"),
            model_id=descriptor.model_id,
            private_memory_namespace=f"{case.case_id}-{arm.lower()}-coordinator-memory",
            harness_capabilities=("formal_receipt_read", "route_proposal"),
            credit_subject_id=f"credit-{descriptor.agent_id}",
        )
        if provider_mode == "live":
            provider = _recording_live(
                recordings, "deepseek", "deepseek-v4-flash", "cognitive_deliberation_coordination", 1800
            )
            adapter: Any = ProviderCognitiveAgentAdapter(
                f"live-coordinator-{case.case_id}-{arm.lower()}", ProviderTaskRouter([provider])
            )
        else:
            adapter = ScriptedCoordinatorAdapter(coordinator)
        return CognitiveCoordinationRuntime(
            coordinator=coordinator,
            adapter=adapter,
            workspace_root=workspace_root,
            max_cycles=5,
            max_role_executions_per_role=1,
        )

    trial_spec = CognitiveExecutionTrialSpec(
        trial_id=f"{case.case_id}-three-arm-trial",
        objective=case.objective,
        project_scope=case.scope,
        evidence_refs=case.evidence_refs,
        evidence_payload=case.evidence_payload,
        finding_catalog=case.finding_catalog,
        frozen_gate_refs=tuple(f"source-hash://{item['sha256']}" for item in case.source_inventory),
        stop_conditions=("all public findings classified", "authorized provider budget exhausted"),
        budget=decision.budget,
        kernel_authorization_ref=f"kernel://{case.case_id}/three-arm-trial",
    )
    runtime = CognitiveTeamExecutionRuntime(
        execution_id=f"{case.case_id}-team-execution",
        formation_runtime=formation,
        registry=registry,
        trial_spec=trial_spec,
        team_adapters=team_adapters,
        solo_routers={"framer-deepseek": ProviderTaskRouter([solo_adapter])},
        normalization_routers={
            "fixed-3": ProviderTaskRouter([fixed_norm]),
            "dynamic-3": ProviderTaskRouter([dynamic_norm]),
        },
        trial_harness=FrozenFindingTrialHarness(
            f"{case.case_id}-hidden-finding-harness", case.hidden_truths
        ),
        workspace_root=output_dir / "execution-runtime",
        coordination_runtime_factory=coordinator_factory if coordinated else None,
    )
    return runtime, recordings


def _build_return_pack(output_dir: Path) -> Path:
    path = output_dir / "AgentOS_CognitiveTeamExecution_ProjectSource_ReturnPack_v0_1.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(output_dir).as_posix())
    return path


def _manifest(output_dir: Path, status: str) -> dict[str, Any]:
    files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "manifest.json",
            "AgentOS_CognitiveTeamExecution_ProjectSource_ReturnPack_v0_1.zip",
        }:
            files.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    payload = {"status": status, "created_at": _utc_now(), "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    _write_json(output_dir / "manifest.json", payload)
    return payload


def run_case(
    case: ProjectTrialCase,
    output_dir: Path,
    *,
    provider_mode: str = "scripted",
    coordinated: bool = True,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "source_hash_inventory.json", case.source_inventory)
    runtime, recordings = _build_runtime(case, output_dir, provider_mode, coordinated)
    runtime.execute_arms(best_member_agent_id="framer-deepseek")
    evaluation = runtime.evaluate_arms()
    ledger = CreditLedger(JsonlCreditEventStore(output_dir / "credit_events.jsonl"))
    feedback = runtime.apply_credit_feedback(ledger)
    snapshot = runtime.snapshot()
    task_audit = [
        {
            "task_kind": task.task_kind,
            "task_id": task.task_id,
            "inputs_hash": _hash_payload(task.inputs),
            "hidden_truth_key_present": _contains_key(task.inputs, HIDDEN_KEYS),
        }
        for adapter in recordings
        for task in adapter.tasks
    ]
    by_arm = {item.arm: item for item in snapshot.arm_results}
    gates = {
        "three_arms_completed": set(by_arm) == {ARM_BEST_MEMBER, ARM_FIXED_TEAM, ARM_DYNAMIC_TEAM},
        "team_roles_actually_executed": len(by_arm[ARM_FIXED_TEAM].formal_messages) == 4
        and len(by_arm[ARM_DYNAMIC_TEAM].formal_messages) == 4,
        "all_arm_replays_valid": all(item["valid"] for item in runtime.verify_arm_replays().values()),
        "execution_replay_valid": runtime.verify_replay()["valid"],
        "hidden_truth_absent_from_provider_inputs": bool(task_audit)
        and not any(item["hidden_truth_key_present"] for item in task_audit),
        "harness_owns_observed_cbit": all(
            receipt.harness_owned and not receipt.semantic_provider_used for receipt in snapshot.harness_receipts
        ),
        "separate_credit_subjects": ledger.profile(evaluation.best_member_subject_id).subject_kind == "agent"
        and ledger.profile(evaluation.fixed_team_subject_id).subject_kind == "team"
        and ledger.profile(evaluation.dynamic_team_subject_id).subject_kind == "team",
        "coordinator_protocol_equal": (not coordinated)
        or by_arm[ARM_FIXED_TEAM].coordinator_protocol_hash == by_arm[ARM_DYNAMIC_TEAM].coordinator_protocol_hash,
    }
    if provider_mode == "scripted":
        gates["fixture_dynamic_arm_outperforms"] = (
            evaluation.verdict_vs_best_member == "OUTPERFORMS"
            and evaluation.verdict_vs_fixed_team == "OUTPERFORMS"
        )
    status = "PASS" if all(gates.values()) else "FAIL"
    result = {
        "smoke_id": f"{case.case_id}-cognitive-team-execution-{provider_mode}",
        "status": status,
        "created_at": _utc_now(),
        "provider_mode": provider_mode,
        "coordinated": coordinated,
        "gates": gates,
        "counterfactual_evaluation": evaluation.as_dict(),
        "harness_receipts": [item.as_dict() for item in snapshot.harness_receipts],
        "credit_feedback": feedback.as_dict(),
        "credit_profiles": [ledger.profile(subject).as_dict() for subject in (
            evaluation.best_member_subject_id,
            evaluation.fixed_team_subject_id,
            evaluation.dynamic_team_subject_id,
        )],
        "execution_snapshot_hash": _hash_payload(snapshot.as_dict()),
        "measurement_boundary": (
            "Observed Cbit is scored mechanically by the hidden finding Harness. Provider semantic quality is "
            "supporting evidence and does not own truth, authorization, or final candidate state."
        ),
        "provider_diversity_boundary": (
            "Live mode validates independent role contexts and model-bound execution within DeepSeek after a separately "
            "preserved Moonshot provider-unavailable run; it is not evidence for live multi-provider robustness."
            if provider_mode == "live"
            else "Scripted mode exercises the two-provider structural boundary with deterministic fixture adapters."
        ),
        "return_pack": str(
            output_dir / "AgentOS_CognitiveTeamExecution_ProjectSource_ReturnPack_v0_1.zip"
        ),
        "manifest_path": str(output_dir / "manifest.json"),
    }
    _write_json(output_dir / "execution_snapshot.json", snapshot.as_dict())
    _write_json(output_dir / "provider_task_audit.json", task_audit)
    _write_json(output_dir / "smoke_result.json", result)
    _manifest(output_dir, status)
    _build_return_pack(output_dir)
    return result


def _case_loader(case_id: str) -> ProjectTrialCase:
    return {
        "life-cog3r": load_life_case,
        "math-cbit1": load_math_cbit1_case,
        "ocs1r2": load_ocs1r2_case,
    }[case_id]()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("life-cog3r", "math-cbit1", "ocs1r2"), required=True)
    parser.add_argument("--provider-mode", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--without-coordinator", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or (
        REPO_ROOT
        / "outputs"
        / f"cognitive_team_execution_{args.case}_{args.provider_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    try:
        result = run_case(
            _case_loader(args.case),
            output_dir,
            provider_mode=args.provider_mode,
            coordinated=not args.without_coordinator,
        )
    except Exception as exc:
        failure = {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:1000]}
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(output_dir / "smoke_failure.json", failure)
        print(json.dumps(failure, indent=2))
        return 1
    print(json.dumps({"status": result["status"], "output_dir": str(output_dir)}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
