"""Run calibrated local collaboration protocols v0.4 through v0.25."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
CORE_ROOT = REPO_ROOT / "agentos_core_slim_v0"
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(PACK_ROOT))

from local_collective_cognition.benchmark_routing_calibration import routing_calibration_receipt_from_dict  # noqa: E402
from local_collective_cognition.calibrated_protocol import CalibratedCollaborationProtocol  # noqa: E402
from local_collective_cognition.calibration_workflow import run_routing_calibration  # noqa: E402
from local_collective_cognition.calibrated_resolution_protocol import CalibratedResolutionProtocol  # noqa: E402
from local_collective_cognition.calibrated_resolution_workflow import build_calibrated_resolution_state  # noqa: E402
from local_collective_cognition.context_resolution_protocol import ContextResolutionProtocol  # noqa: E402
from local_collective_cognition.context_resolution_workflow import build_context_resolution_state  # noqa: E402
from local_collective_cognition.iterated_context_protocol import IteratedContextResolutionProtocol  # noqa: E402
from local_collective_cognition.iterated_context_workflow import build_iterated_context_state  # noqa: E402
from local_collective_cognition.case_adjudication_protocol import CaseAdjudicationProtocol  # noqa: E402
from local_collective_cognition.case_adjudication_workflow import build_case_adjudication_state  # noqa: E402
from local_collective_cognition.verified_case_protocol import VerifiedCaseAdjudicationProtocol  # noqa: E402
from local_collective_cognition.verified_case_workflow import build_verified_case_state  # noqa: E402
from local_collective_cognition.single_expression_protocol import SingleExpressionAdjudicationProtocol  # noqa: E402
from local_collective_cognition.single_expression_workflow import build_single_expression_state  # noqa: E402
from local_collective_cognition.candidate_revision_protocol import CandidateRevisionProtocol  # noqa: E402
from local_collective_cognition.candidate_revision_workflow import build_candidate_revision_state  # noqa: E402
from local_collective_cognition.typed_derivation_protocol import TypedDerivationProtocol  # noqa: E402
from local_collective_cognition.typed_derivation_workflow import build_typed_derivation_state  # noqa: E402
from local_collective_cognition.iterative_derivation_protocol import IterativeDerivationProtocol  # noqa: E402
from local_collective_cognition.iterative_derivation_workflow import build_iterative_derivation_state  # noqa: E402
from local_collective_cognition.staged_derivation_protocol import StagedDerivationProtocol  # noqa: E402
from local_collective_cognition.staged_derivation_workflow import build_staged_derivation_state  # noqa: E402
from local_collective_cognition.constrained_tool_protocol import ConstrainedToolProtocol  # noqa: E402
from local_collective_cognition.constrained_tool_workflow import build_constrained_tool_state  # noqa: E402
from local_collective_cognition.hierarchical_tool_protocol import HierarchicalToolProtocol  # noqa: E402
from local_collective_cognition.hierarchical_tool_workflow import build_hierarchical_tool_state  # noqa: E402
from local_collective_cognition.plan_intent_protocol import PlanIntentProtocol  # noqa: E402
from local_collective_cognition.plan_intent_workflow import build_plan_intent_state  # noqa: E402
from local_collective_cognition.problem_formulation_protocol import ProblemFormulationProtocol  # noqa: E402
from local_collective_cognition.problem_formulation_workflow import build_problem_formulation_state  # noqa: E402
from local_collective_cognition.local_problem_formulation_provider import LocalProblemFormulationAdapter  # noqa: E402
from local_collective_cognition.problem_dialogue_protocol import ProblemDialogueProtocol  # noqa: E402
from local_collective_cognition.problem_dialogue_workflow import build_problem_dialogue_state  # noqa: E402
from local_collective_cognition.local_problem_dialogue_provider import LocalProblemDialogueAdapter  # noqa: E402
from local_collective_cognition.collective_protocol import (  # noqa: E402
    PILOT_TASK_KINDS,
    LocalCollectiveCognitionProtocol,
    role_run_as_dict,
    role_run_from_dict,
)
from local_collective_cognition.holdout_benchmark import HOLDOUT_ITEM_DOMAINS, build_holdout_harness  # noqa: E402
from local_collective_cognition.holdout_v2_benchmark import build_holdout_v2_harness  # noqa: E402
from local_collective_cognition.holdout_v3_benchmark import build_holdout_v3_harness  # noqa: E402
from local_collective_cognition.holdout_v4_benchmark import HOLDOUT_V4_ITEM_DOMAINS, build_holdout_v4_harness  # noqa: E402
from local_collective_cognition.holdout_v5_benchmark import build_holdout_v5_harness  # noqa: E402
from local_collective_cognition.holdout_v6_benchmark import (  # noqa: E402
    HOLDOUT_V6_ITEM_DOMAINS,
    HOLDOUT_V6_ITEM_FINGERPRINTS,
    build_holdout_v6_harness,
)
from local_collective_cognition.holdout_v7_benchmark import build_holdout_v7_harness  # noqa: E402
from local_collective_cognition.holdout_v8_benchmark import build_holdout_v8_harness  # noqa: E402
from local_collective_cognition.holdout_v9_benchmark import build_holdout_v9_harness  # noqa: E402
from local_collective_cognition.holdout_v10_benchmark import build_holdout_v10_harness  # noqa: E402
from local_collective_cognition.holdout_v11_benchmark import build_holdout_v11_harness  # noqa: E402
from local_collective_cognition.holdout_v12_benchmark import build_holdout_v12_harness  # noqa: E402
from local_collective_cognition.holdout_v13_benchmark import build_holdout_v13_harness  # noqa: E402
from local_collective_cognition.holdout_v14_benchmark import build_holdout_v14_harness  # noqa: E402
from local_collective_cognition.holdout_v15_benchmark import build_holdout_v15_harness  # noqa: E402
from local_collective_cognition.holdout_v16_benchmark import build_holdout_v16_harness  # noqa: E402
from local_collective_cognition.holdout_v17_benchmark import build_holdout_v17_harness  # noqa: E402
from local_collective_cognition.holdout_v18_benchmark import build_holdout_v18_harness  # noqa: E402
from local_collective_cognition.holdout_v19_benchmark import build_holdout_v19_harness  # noqa: E402
from local_collective_cognition.holdout_v20_benchmark import build_holdout_v20_harness  # noqa: E402
from local_collective_cognition.holdout_v21_benchmark import build_holdout_v21_harness  # noqa: E402
from local_collective_cognition.holdout_v22_benchmark import build_holdout_v22_harness  # noqa: E402
from local_collective_cognition.holdout_v23_benchmark import build_holdout_v23_harness  # noqa: E402
from local_collective_cognition.evidence_gated_protocol import EvidenceGatedCollaborationProtocol  # noqa: E402
from local_collective_cognition.contextual_arbitration_protocol import ContextualArbitrationProtocol  # noqa: E402
from local_collective_cognition.fingerprint_history import build_historical_fingerprint_credit  # noqa: E402
from local_collective_cognition.hierarchical_fingerprint_credit import build_micro_probe_schedule  # noqa: E402
from local_collective_cognition.local_transformers_provider import LocalTransformersModelSpec  # noqa: E402
from local_collective_cognition.local_plan_intent_provider import (  # noqa: E402
    PlanIntentTransformersResidentPool,
    LocalPlanIntentAdapter,
)
from local_collective_cognition.ollama_provider import OllamaJsonAdapter  # noqa: E402
from local_collective_cognition.operator_competition_workflow import build_operator_competition_state  # noqa: E402
from local_collective_cognition.independent_resolution_protocol import IndependentDisagreementResolutionProtocol  # noqa: E402
from local_collective_cognition.provider_telemetry import ProviderTelemetryLedger  # noqa: E402
from local_collective_cognition.routing_calibration import build_calibrated_profiles  # noqa: E402
from local_collective_cognition.reliability_lifecycle import ReliabilityLifecycleLedger, build_shadow_exploration_schedule  # noqa: E402
from local_collective_cognition.reliability_lifecycle_protocol import ReliabilityLifecycleCollaborationProtocol  # noqa: E402
from local_collective_cognition.resolution_lifecycle_workflow import build_resolution_lifecycle_state  # noqa: E402
from local_collective_cognition.structural_fingerprint_protocol import StructuralFingerprintCollaborationProtocol  # noqa: E402
from local_collective_cognition.structural_operator_protocol import StructuralOperatorCompetitionProtocol  # noqa: E402


def wait_for_ollama_release(base_url: str, model_id: str, timeout_seconds: int = 180) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        loaded = {str(item.get("name") or item.get("model") or "") for item in payload.get("models", [])}
        if model_id not in loaded:
            return
        time.sleep(2)
    raise TimeoutError("ollama_model_release_timeout")


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def main(protocol_version: str = "v0.4") -> int:
    if protocol_version not in {"v0.4", "v0.5", "v0.6", "v0.7", "v0.8", "v0.9", "v0.10", "v0.11", "v0.12", "v0.13", "v0.14", "v0.15", "v0.16", "v0.17", "v0.18", "v0.19", "v0.20", "v0.21", "v0.22", "v0.23", "v0.24", "v0.25"}:
        raise ValueError("local_collaboration_protocol_version_invalid")
    evidence_gated = protocol_version in {"v0.5", "v0.6", "v0.7"}
    lifecycle_enabled = protocol_version in {"v0.6", "v0.7"}
    contextual_enabled = protocol_version == "v0.7"
    structural_enabled = protocol_version in {"v0.8", "v0.9", "v0.10", "v0.11", "v0.12", "v0.13", "v0.14", "v0.15", "v0.16", "v0.17", "v0.18", "v0.19", "v0.20", "v0.21", "v0.22", "v0.23", "v0.24", "v0.25"}
    operator_enabled = protocol_version in {"v0.9", "v0.10", "v0.11", "v0.12", "v0.13", "v0.14", "v0.15", "v0.16", "v0.17", "v0.18", "v0.19", "v0.20", "v0.21", "v0.22", "v0.23", "v0.24", "v0.25"}
    resolution_enabled = protocol_version == "v0.10"
    calibrated_resolution_enabled = protocol_version == "v0.11"
    context_resolution_enabled = protocol_version == "v0.12"
    iterated_context_enabled = protocol_version == "v0.13"
    case_adjudication_enabled = protocol_version == "v0.14"
    verified_case_enabled = protocol_version == "v0.15"
    single_expression_enabled = protocol_version == "v0.16"
    candidate_revision_enabled = protocol_version == "v0.17"
    typed_derivation_enabled = protocol_version == "v0.18"
    iterative_derivation_enabled = protocol_version == "v0.19"
    staged_derivation_enabled = protocol_version == "v0.20"
    constrained_tool_enabled = protocol_version == "v0.21"
    hierarchical_tool_enabled = protocol_version == "v0.22"
    plan_intent_enabled = protocol_version == "v0.23"
    problem_formulation_enabled = protocol_version == "v0.24"
    problem_dialogue_enabled = protocol_version == "v0.25"
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-path", default=r"D:\model\Llama-3.2-1B-Instruct")
    parser.add_argument("--qwen-path", default=r"D:\model\models--Qwen--Qwen2.5-1.5B-Instruct\main")
    parser.add_argument("--gemma-path", default=r"D:\model\gemma-2-2b-it")
    parser.add_argument("--ollama-model", default="deepseek-r1:32b")
    parser.add_argument("--calibration-cache", default="outputs/calibrated_collaboration_calibration_cache_v0_4.json")
    parser.add_argument("--lifecycle-source", default="outputs/evidence_gated_collaboration_pilot_v0_5.json")
    parser.add_argument("--lifecycle-source-v06", default="outputs/reliability_lifecycle_pilot_v0_6.json")
    parser.add_argument("--fingerprint-source-v04", default="outputs/calibrated_collaboration_pilot_v0_4.json")
    parser.add_argument("--fingerprint-source-v05", default="outputs/evidence_gated_collaboration_pilot_v0_5.json")
    parser.add_argument("--fingerprint-source-v06", default="outputs/reliability_lifecycle_pilot_v0_6.json")
    parser.add_argument("--fingerprint-source-v07", default="outputs/contextual_arbitration_pilot_v0_7.json")
    parser.add_argument("--fingerprint-source-v08", default="outputs/structural_fingerprint_pilot_v0_8.json")
    parser.add_argument("--fingerprint-source-v09", default="outputs/structural_operator_pilot_v0_9.json")
    parser.add_argument("--fingerprint-source-v10", default="outputs/resolution_lifecycle_pilot_v0_10.json")
    parser.add_argument("--fingerprint-source-v11", default="outputs/calibrated_resolution_pilot_v0_11.json")
    parser.add_argument("--fingerprint-source-v12", default="outputs/context_resolution_pilot_v0_12.json")
    parser.add_argument("--fingerprint-source-v13", default="outputs/iterated_context_pilot_v0_13.json")
    parser.add_argument("--fingerprint-source-v14", default="outputs/case_adjudication_pilot_v0_14.json")
    parser.add_argument("--fingerprint-source-v15", default="outputs/verified_case_pilot_v0_15.json")
    parser.add_argument("--fingerprint-source-v16", default="outputs/single_expression_pilot_v0_16.json")
    parser.add_argument("--fingerprint-source-v17", default="outputs/candidate_revision_pilot_v0_17.json")
    parser.add_argument("--fingerprint-source-v18", default="outputs/typed_derivation_pilot_v0_18.json")
    parser.add_argument("--fingerprint-source-v19", default="outputs/iterative_derivation_pilot_v0_19.json")
    parser.add_argument("--fingerprint-source-v20", default="outputs/staged_derivation_pilot_v0_20.json")
    parser.add_argument("--fingerprint-source-v21", default="outputs/constrained_tool_pilot_v0_21.json")
    parser.add_argument("--fingerprint-source-v22", default="outputs/hierarchical_tool_pilot_v0_22.json")
    parser.add_argument("--fingerprint-source-v23", default="outputs/plan_intent_pilot_v0_23.json")
    parser.add_argument("--fingerprint-source-v24", default="outputs/problem_formulation_pilot_v0_24.json")
    parser.add_argument("--baseline-cache", default="outputs/hierarchical_tool_32b_holdout_cache_v0_22.json" if hierarchical_tool_enabled else "outputs/constrained_tool_32b_holdout_cache_v0_21.json" if constrained_tool_enabled else "outputs/staged_derivation_32b_holdout_cache_v0_20.json" if staged_derivation_enabled else "outputs/iterative_derivation_32b_holdout_cache_v0_19.json" if iterative_derivation_enabled else "outputs/typed_derivation_32b_holdout_cache_v0_18.json" if typed_derivation_enabled else "outputs/candidate_revision_32b_holdout_cache_v0_17.json" if candidate_revision_enabled else "outputs/single_expression_32b_holdout_cache_v0_16.json" if single_expression_enabled else "outputs/verified_case_32b_holdout_cache_v0_15.json" if verified_case_enabled else "outputs/case_adjudication_32b_holdout_cache_v0_14.json" if case_adjudication_enabled else "outputs/iterated_context_32b_holdout_cache_v0_13.json" if iterated_context_enabled else "outputs/context_resolution_32b_holdout_cache_v0_12.json" if context_resolution_enabled else "outputs/calibrated_resolution_32b_holdout_cache_v0_11.json" if calibrated_resolution_enabled else "outputs/resolution_lifecycle_32b_holdout_cache_v0_10.json" if resolution_enabled else "outputs/structural_operator_32b_holdout_cache_v0_9.json" if operator_enabled else "outputs/structural_fingerprint_32b_holdout_cache_v0_8.json" if structural_enabled else "outputs/contextual_arbitration_32b_holdout_cache_v0_7.json" if contextual_enabled else "outputs/reliability_lifecycle_32b_holdout_cache_v0_6.json" if lifecycle_enabled else "outputs/evidence_gated_collaboration_32b_holdout_cache_v0_5.json" if evidence_gated else "outputs/calibrated_collaboration_32b_holdout_cache_v0_4.json")
    parser.add_argument("--output", default="outputs/hierarchical_tool_pilot_v0_22.json" if hierarchical_tool_enabled else "outputs/constrained_tool_pilot_v0_21.json" if constrained_tool_enabled else "outputs/staged_derivation_pilot_v0_20.json" if staged_derivation_enabled else "outputs/iterative_derivation_pilot_v0_19.json" if iterative_derivation_enabled else "outputs/typed_derivation_pilot_v0_18.json" if typed_derivation_enabled else "outputs/candidate_revision_pilot_v0_17.json" if candidate_revision_enabled else "outputs/single_expression_pilot_v0_16.json" if single_expression_enabled else "outputs/verified_case_pilot_v0_15.json" if verified_case_enabled else "outputs/case_adjudication_pilot_v0_14.json" if case_adjudication_enabled else "outputs/iterated_context_pilot_v0_13.json" if iterated_context_enabled else "outputs/context_resolution_pilot_v0_12.json" if context_resolution_enabled else "outputs/calibrated_resolution_pilot_v0_11.json" if calibrated_resolution_enabled else "outputs/resolution_lifecycle_pilot_v0_10.json" if resolution_enabled else "outputs/structural_operator_pilot_v0_9.json" if operator_enabled else "outputs/structural_fingerprint_pilot_v0_8.json" if structural_enabled else "outputs/contextual_arbitration_pilot_v0_7.json" if contextual_enabled else "outputs/reliability_lifecycle_pilot_v0_6.json" if lifecycle_enabled else "outputs/evidence_gated_collaboration_pilot_v0_5.json" if evidence_gated else "outputs/calibrated_collaboration_pilot_v0_4.json")
    if plan_intent_enabled:
        parser.set_defaults(
            baseline_cache="outputs/plan_intent_32b_holdout_cache_v0_23.json",
            output="outputs/plan_intent_pilot_v0_23.json",
        )
    if problem_formulation_enabled:
        parser.set_defaults(
            baseline_cache="outputs/problem_formulation_32b_holdout_cache_v0_24.json",
            output="outputs/problem_formulation_pilot_v0_24.json",
        )
    if problem_dialogue_enabled:
        parser.set_defaults(
            baseline_cache="outputs/problem_dialogue_32b_holdout_cache_v0_25.json",
            output="outputs/problem_dialogue_pilot_v0_25.json",
        )
    args = parser.parse_args()

    specs = (
        LocalTransformersModelSpec("llama-3.2-1b-instruct", args.llama_path),
        LocalTransformersModelSpec("qwen2.5-1.5b-instruct", args.qwen_path),
        LocalTransformersModelSpec("gemma-2-2b-it", args.gemma_path),
    )
    ledger = ProviderTelemetryLedger()
    pool = PlanIntentTransformersResidentPool(specs)
    adapter_class = LocalProblemDialogueAdapter if problem_dialogue_enabled else LocalProblemFormulationAdapter if problem_formulation_enabled else LocalPlanIntentAdapter
    small_adapters = {
        spec.model_id: adapter_class(
            provider_id=f"local-transformers-{spec.model_id}", model_id=spec.model_id,
            task_kinds=PILOT_TASK_KINDS, pool=pool, telemetry_ledger=ledger,
            max_new_tokens=256, max_attempts=2,
        )
        for spec in specs
    }
    baseline = OllamaJsonAdapter(
        provider_id="ollama-local", model_id=args.ollama_model,
        task_kinds=PILOT_TASK_KINDS, telemetry_ledger=ledger,
        timeout_seconds=900, max_new_tokens=256, max_attempts=2,
        thinking_enabled=False, keep_alive=0,
    )

    calibration_cache = _path(args.calibration_cache)
    if calibration_cache.is_file():
        calibration_payload = json.loads(calibration_cache.read_text(encoding="utf-8"))
        calibration_receipt = routing_calibration_receipt_from_dict(calibration_payload["receipt"])
        calibration_reused = True
    else:
        wait_for_ollama_release(baseline.base_url, args.ollama_model)
        pool.load_all()
        calibration_base = LocalCollectiveCognitionProtocol(
            harness=build_holdout_harness(), small_adapters=small_adapters,
            baseline_adapter=baseline, telemetry_ledger=ledger,
            reviewer_model_id="qwen2.5-1.5b-instruct", synthesizer_model_id="gemma-2-2b-it",
        )
        try:
            calibration_runs, _, calibration_receipt = run_routing_calibration(
                base=calibration_base,
                calibration_id="routing-calibration-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                item_domains=HOLDOUT_ITEM_DOMAINS,
            )
        finally:
            pool.unload_all()
        calibration_cache.parent.mkdir(parents=True, exist_ok=True)
        calibration_cache.write_text(json.dumps({
            "receipt": calibration_receipt.as_dict(),
            "runs": [role_run_as_dict(item) for item in calibration_runs],
        }, indent=2, sort_keys=True), encoding="utf-8")
        calibration_reused = False

    profiles, reviewer_ledger = build_calibrated_profiles(calibration_receipt)
    lifecycle_values = {}
    fingerprint_history = None
    pre_v08_sources = (
        (_path(args.fingerprint_source_v04), build_holdout_v2_harness()),
        (_path(args.fingerprint_source_v05), build_holdout_v3_harness()),
        (_path(args.fingerprint_source_v06), build_holdout_v4_harness()),
        (_path(args.fingerprint_source_v07), build_holdout_v5_harness()),
    )
    if problem_dialogue_enabled:
        state = build_problem_dialogue_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
            v19_report_path=_path(args.fingerprint_source_v19),
            v20_report_path=_path(args.fingerprint_source_v20),
            v21_report_path=_path(args.fingerprint_source_v21),
            v22_report_path=_path(args.fingerprint_source_v22),
            v23_report_path=_path(args.fingerprint_source_v23),
            v24_report_path=_path(args.fingerprint_source_v24),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif problem_formulation_enabled:
        state = build_problem_formulation_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
            v19_report_path=_path(args.fingerprint_source_v19),
            v20_report_path=_path(args.fingerprint_source_v20),
            v21_report_path=_path(args.fingerprint_source_v21),
            v22_report_path=_path(args.fingerprint_source_v22),
            v23_report_path=_path(args.fingerprint_source_v23),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif plan_intent_enabled:
        state = build_plan_intent_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
            v19_report_path=_path(args.fingerprint_source_v19),
            v20_report_path=_path(args.fingerprint_source_v20),
            v21_report_path=_path(args.fingerprint_source_v21),
            v22_report_path=_path(args.fingerprint_source_v22),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif hierarchical_tool_enabled:
        state = build_hierarchical_tool_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
            v19_report_path=_path(args.fingerprint_source_v19),
            v20_report_path=_path(args.fingerprint_source_v20),
            v21_report_path=_path(args.fingerprint_source_v21),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif constrained_tool_enabled:
        state = build_constrained_tool_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
            v19_report_path=_path(args.fingerprint_source_v19),
            v20_report_path=_path(args.fingerprint_source_v20),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif staged_derivation_enabled:
        state = build_staged_derivation_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
            v19_report_path=_path(args.fingerprint_source_v19),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif iterative_derivation_enabled:
        state = build_iterative_derivation_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
            v18_report_path=_path(args.fingerprint_source_v18),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif typed_derivation_enabled:
        state = build_typed_derivation_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
            v17_report_path=_path(args.fingerprint_source_v17),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif candidate_revision_enabled:
        state = build_candidate_revision_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
            v16_report_path=_path(args.fingerprint_source_v16),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif single_expression_enabled:
        state = build_single_expression_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
            v15_report_path=_path(args.fingerprint_source_v15),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif verified_case_enabled:
        state = build_verified_case_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
            v14_report_path=_path(args.fingerprint_source_v14),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif case_adjudication_enabled:
        state = build_case_adjudication_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
            v13_report_path=_path(args.fingerprint_source_v13),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif iterated_context_enabled:
        state = build_iterated_context_state(
            base_profiles=profiles, calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
            v12_report_path=_path(args.fingerprint_source_v12),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif context_resolution_enabled:
        state = build_context_resolution_state(
            base_profiles=profiles,
            calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
            v11_report_path=_path(args.fingerprint_source_v11),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif calibrated_resolution_enabled:
        state = build_calibrated_resolution_state(
            base_profiles=profiles,
            calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
            v10_report_path=_path(args.fingerprint_source_v10),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif resolution_enabled:
        state = build_resolution_lifecycle_state(
            base_profiles=profiles,
            calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
            v09_report_path=_path(args.fingerprint_source_v09),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif operator_enabled:
        state = build_operator_competition_state(
            base_profiles=profiles,
            calibration_cache=calibration_cache,
            pre_v08_sources=pre_v08_sources,
            v08_report_path=_path(args.fingerprint_source_v08),
        )
        profiles = state.pop("profiles")
        fingerprint_history = state.pop("fingerprint_credit_history")
        lifecycle_values = state
    elif structural_enabled:
        profiles, fingerprint_snapshot, fingerprint_history = build_historical_fingerprint_credit(
            base_profiles=profiles,
            calibration_cache=calibration_cache,
            report_sources=(
                (_path(args.fingerprint_source_v04), build_holdout_v2_harness()),
                (_path(args.fingerprint_source_v05), build_holdout_v3_harness()),
                (_path(args.fingerprint_source_v06), build_holdout_v4_harness()),
                (_path(args.fingerprint_source_v07), build_holdout_v5_harness()),
            ),
        )
        lifecycle_values = {
            "fingerprint_credit_snapshot": fingerprint_snapshot,
            "probe_schedule": build_micro_probe_schedule(
                item_domains=HOLDOUT_V6_ITEM_DOMAINS,
                item_fingerprints=HOLDOUT_V6_ITEM_FINGERPRINTS,
                profiles=profiles,
                budget=3,
            ),
        }
    if lifecycle_enabled:
        lifecycle_source = _path(args.lifecycle_source)
        lifecycle_payload = json.loads(lifecycle_source.read_text(encoding="utf-8"))
        lifecycle_ledger = ReliabilityLifecycleLedger(
            calibration_receipt=calibration_receipt, base_profiles=profiles,
        )
        cycle_candidate = lifecycle_ledger.ingest_candidate(
            cycle_id=lifecycle_payload["experiment_id"], sequence=1,
            diagnostics=lifecycle_payload["posthoc_domain_diagnostics"],
        )
        promotion_receipt = lifecycle_ledger.promote(
            candidate_hash=cycle_candidate.candidate_hash,
            validation_ref=hashlib.sha256(lifecycle_source.read_bytes()).hexdigest(),
        )
        operator_receipt = None
        if contextual_enabled:
            lifecycle_source_v06 = _path(args.lifecycle_source_v06)
            lifecycle_payload_v06 = json.loads(lifecycle_source_v06.read_text(encoding="utf-8"))
            cycle_candidate = lifecycle_ledger.ingest_candidate(
                cycle_id=lifecycle_payload_v06["experiment_id"], sequence=2,
                diagnostics=lifecycle_payload_v06["posthoc_domain_diagnostics"],
            )
            promotion_receipt = lifecycle_ledger.promote(
                candidate_hash=cycle_candidate.candidate_hash,
                validation_ref=hashlib.sha256(lifecycle_source_v06.read_bytes()).hexdigest(),
            )
            operator_receipt = build_holdout_v4_harness().calibrate_routing(
                experiment_id=lifecycle_payload_v06["experiment_id"],
                source_report_hash=hashlib.sha256(lifecycle_source_v06.read_bytes()).hexdigest(),
                route_decisions=tuple(lifecycle_payload_v06["route_decisions"]),
                majority_answer_vector=lifecycle_payload_v06["majority_arm"]["answer_vector"],
                solo_answer_vectors=tuple(item["answer_vector"] for item in lifecycle_payload_v06["solo_arms"]),
                item_domains=HOLDOUT_V4_ITEM_DOMAINS,
            )
        profiles, lifecycle_snapshot = lifecycle_ledger.snapshot()
        lifecycle_values = {
            "lifecycle_snapshot": lifecycle_snapshot,
            "cycle_candidate": cycle_candidate,
            "promotion_receipt": promotion_receipt,
            "profile_receipt_hash": lifecycle_snapshot["snapshot_hash"],
            "exploration_schedule": {} if contextual_enabled else build_shadow_exploration_schedule(
                item_domains=HOLDOUT_V4_ITEM_DOMAINS, profiles=profiles, budget=2,
            ),
        }
        if contextual_enabled:
            lifecycle_values["operator_receipt"] = operator_receipt
    evaluation_base = LocalCollectiveCognitionProtocol(
        harness=build_holdout_v23_harness() if problem_dialogue_enabled else build_holdout_v22_harness() if problem_formulation_enabled else build_holdout_v21_harness() if plan_intent_enabled else build_holdout_v20_harness() if hierarchical_tool_enabled else build_holdout_v19_harness() if constrained_tool_enabled else build_holdout_v18_harness() if staged_derivation_enabled else build_holdout_v17_harness() if iterative_derivation_enabled else build_holdout_v16_harness() if typed_derivation_enabled else build_holdout_v15_harness() if candidate_revision_enabled else build_holdout_v14_harness() if single_expression_enabled else build_holdout_v13_harness() if verified_case_enabled else build_holdout_v12_harness() if case_adjudication_enabled else build_holdout_v11_harness() if iterated_context_enabled else build_holdout_v10_harness() if context_resolution_enabled else build_holdout_v9_harness() if calibrated_resolution_enabled else build_holdout_v8_harness() if resolution_enabled else build_holdout_v7_harness() if operator_enabled else build_holdout_v6_harness() if structural_enabled else build_holdout_v5_harness() if contextual_enabled else build_holdout_v4_harness() if lifecycle_enabled else build_holdout_v3_harness() if evidence_gated else build_holdout_v2_harness(), small_adapters=small_adapters,
        baseline_adapter=baseline, telemetry_ledger=ledger,
        reviewer_model_id="qwen2.5-1.5b-instruct", synthesizer_model_id="gemma-2-2b-it",
    )
    protocol_class = ProblemDialogueProtocol if problem_dialogue_enabled else ProblemFormulationProtocol if problem_formulation_enabled else PlanIntentProtocol if plan_intent_enabled else HierarchicalToolProtocol if hierarchical_tool_enabled else ConstrainedToolProtocol if constrained_tool_enabled else StagedDerivationProtocol if staged_derivation_enabled else IterativeDerivationProtocol if iterative_derivation_enabled else TypedDerivationProtocol if typed_derivation_enabled else CandidateRevisionProtocol if candidate_revision_enabled else SingleExpressionAdjudicationProtocol if single_expression_enabled else VerifiedCaseAdjudicationProtocol if verified_case_enabled else CaseAdjudicationProtocol if case_adjudication_enabled else IteratedContextResolutionProtocol if iterated_context_enabled else ContextResolutionProtocol if context_resolution_enabled else CalibratedResolutionProtocol if calibrated_resolution_enabled else IndependentDisagreementResolutionProtocol if resolution_enabled else StructuralOperatorCompetitionProtocol if operator_enabled else StructuralFingerprintCollaborationProtocol if structural_enabled else ContextualArbitrationProtocol if contextual_enabled else ReliabilityLifecycleCollaborationProtocol if lifecycle_enabled else EvidenceGatedCollaborationProtocol if evidence_gated else CalibratedCollaborationProtocol
    protocol = protocol_class(
        base=evaluation_base, calibration_receipt=calibration_receipt,
        profiles=profiles, reviewer_ledger=reviewer_ledger,
        **lifecycle_values,
    )

    baseline_cache = _path(args.baseline_cache)
    cached_baseline = role_run_from_dict(json.loads(baseline_cache.read_text(encoding="utf-8"))) if baseline_cache.is_file() else None

    def save_baseline(run):
        baseline_cache.parent.mkdir(parents=True, exist_ok=True)
        baseline_cache.write_text(json.dumps(role_run_as_dict(run), indent=2, sort_keys=True), encoding="utf-8")

    def prepare_small_models():
        if cached_baseline is None:
            wait_for_ollama_release(baseline.base_url, args.ollama_model)
        return pool.load_all()

    try:
        report = protocol.run(
            ("problem-dialogue-" if problem_dialogue_enabled else "problem-formulation-" if problem_formulation_enabled else "plan-intent-" if plan_intent_enabled else "constrained-tool-" if constrained_tool_enabled else "staged-derivation-" if staged_derivation_enabled else "iterative-derivation-" if iterative_derivation_enabled else "typed-derivation-" if typed_derivation_enabled else "candidate-revision-" if candidate_revision_enabled else "single-expression-" if single_expression_enabled else "verified-case-" if verified_case_enabled else "case-adjudication-" if case_adjudication_enabled else "iterated-context-" if iterated_context_enabled else "context-resolution-" if context_resolution_enabled else "calibrated-resolution-" if calibrated_resolution_enabled else "resolution-lifecycle-" if resolution_enabled else "structural-operator-" if operator_enabled else "structural-fingerprint-" if structural_enabled else "contextual-arbitration-" if contextual_enabled else "reliability-lifecycle-" if lifecycle_enabled else "evidence-gated-collaboration-" if evidence_gated else "calibrated-collaboration-") + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            baseline_run=cached_baseline,
            baseline_observer=save_baseline,
            prepare_small_models=prepare_small_models,
        )
    finally:
        pool.unload_all()
    report["protocol"]["calibration_reused_from_cache"] = calibration_reused
    report["protocol"]["baseline_reused_from_cache"] = cached_baseline is not None
    if fingerprint_history is not None:
        report["fingerprint_credit_history"] = fingerprint_history

    output = _path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
