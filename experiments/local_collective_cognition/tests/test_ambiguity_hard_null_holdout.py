from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.ambiguity_discovery_contracts import (  # noqa: E402
    TASK_KIND as DISCOVERY_TASK_KIND,
)
from local_collective_cognition.ambiguity_discovery_runtime import (  # noqa: E402
    AmbiguityDiscoveryRuntime,
)
from local_collective_cognition.ambiguity_hard_null_contracts import (  # noqa: E402
    TASK_KIND as HARD_NULL_TASK_KIND,
    validate_hard_null_coordinator_payload,
)
from local_collective_cognition.ambiguity_hard_null_eval import (  # noqa: E402
    build_hard_null_artifact,
    validate_hard_null_artifact,
)
from local_collective_cognition.ambiguity_hard_null_holdout import (  # noqa: E402
    CASES,
    EVIDENCE_REFS,
    HOLDOUT_SPEC,
    MATERIALITY_CONTROL_HASH,
    RECEIPT_QUALITY_CONTROL_HASH,
    validate_hard_null_holdout_spec,
)
from local_collective_cognition.ambiguity_hard_null_runtime import (  # noqa: E402
    HardNullAmbiguityCoordinatorRuntime,
)
from local_collective_cognition.ambiguity_hard_null_surface import (  # noqa: E402
    FIRST_POSITION_ROLE,
    build_hard_null_surface,
    validate_hard_null_surface,
)
from local_collective_cognition.ambiguity_coordinator_holdout import (  # noqa: E402
    CASES as OLD_COORDINATOR_CASES,
)
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderInvocationTelemetry,
    ProviderTelemetryLedger,
    hash_payload,
)
from local_collective_cognition.unstated_ambiguity_holdout import (  # noqa: E402
    CASES as OLD_DISCOVERY_CASES,
    NULL,
    POSITIVE,
)


class FixtureDiscoveryAdapter:
    def __init__(self, model_id, state):
        self.state = state
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id,
            model_id=model_id,
            task_kinds=(DISCOVERY_TASK_KIND,),
            max_timeout_seconds=120,
        )
        self.telemetry_ledger = ProviderTelemetryLedger()

    def invoke(self, task):
        item_id = task.inputs["public_task"]["item_id"]
        positive = self.state == POSITIVE
        payload = {
            "item_id": item_id,
            "discovery_state": self.state,
            "rival_a": "count" if positive else "",
            "rival_b": "rate" if positive else "",
            "decisive_contrast": "different requested outputs" if positive else "",
            "discriminating_question": "Which output object is intended?" if positive else "",
            "confidence": 0.8,
            "evidence_refs": list(task.allowed_evidence),
        }
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id="telemetry-" + task.task_id,
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="fixture",
            task_id=task.task_id,
            task_kind=task.task_kind,
            task_contract_hash=hash_payload({"task_id": task.task_id}),
            status="COMPLETED",
            input_tokens=10,
            output_tokens=10,
            cached_tokens=0,
            latency_ms=1,
            api_cost=0.0,
            tool_calls=0,
            tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence),
            output_hash=hash_payload(payload),
            thinking_present=False,
            thinking_char_count=0,
            thinking_hash="",
            error_type="",
        )
        self.telemetry_ledger.record(telemetry)
        return {
            "result": payload,
            "usage": {"input_tokens": 10, "output_tokens": 10},
            "provenance_refs": list(task.allowed_evidence),
        }


class FixtureHardNullCoordinatorAdapter:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-deepseek",
            model_id="fixture-coordinator",
            task_kinds=(HARD_NULL_TASK_KIND,),
            max_timeout_seconds=240,
        )
        self.seen_inputs = []

    def invoke(self, task):
        self.seen_inputs.append(task.inputs)
        decisions = []
        for item in task.inputs["batch"]["items"]:
            item_id = item["public_task"]["item_id"]
            expected = next(case.expected_state for case in CASES if case.item_id == item_id)
            positive = expected == POSITIVE
            assessments = [
                {
                    "position": "POSITION_A",
                    "quality_state": (
                        "USABLE_MATERIAL_SUPPORT" if positive else "USABLE_NULL_SUPPORT"
                    ),
                    "task_grounded": True,
                    "rivals_distinct": positive,
                    "output_sensitive": positive,
                },
                {
                    "position": "POSITION_B",
                    "quality_state": "USABLE_NULL_SUPPORT",
                    "task_grounded": True,
                    "rivals_distinct": False,
                    "output_sensitive": False,
                },
            ]
            decisions.append({
                "coordination_item_id": item["coordination_item_id"],
                "receipt_assessments": assessments,
                "materiality_basis": (
                    "MATERIAL_RIVALRY" if positive else "EXPLICITLY_DISAMBIGUATED"
                ),
                "prompt_disambiguates": not positive,
                "final_state": expected,
                "confidence": 0.9,
                "decision_note": "Fixture decision under frozen controls.",
            })
        batch = task.inputs["batch"]
        return {
            "result": {
                "batch_id": batch["batch_id"],
                "decisions": decisions,
                "evidence_refs": list(task.allowed_evidence),
            },
            "usage": {"input_tokens": 100, "output_tokens": 100},
            "provenance_refs": list(task.allowed_evidence),
        }


def _role_and_runs():
    role_commitment = {
        "role_candidates": {
            "ambiguity_proposer": {
                "provider_id": "fixture-proposer", "model_id": "proposer",
            },
            "null_skeptic": {
                "provider_id": "fixture-skeptic", "model_id": "skeptic",
            },
            "semantic_coordinator": {
                "provider_id": "fixture-deepseek", "model_id": "fixture-coordinator",
            },
        },
    }
    role = {**role_commitment, "artifact_hash": hash_payload(role_commitment)}
    discovery = AmbiguityDiscoveryRuntime(
        cases=CASES,
        holdout_spec=HOLDOUT_SPEC,
        spec_validator=validate_hard_null_holdout_spec,
        evidence_refs=EVIDENCE_REFS,
    )
    runs = (
        discovery.evaluate_model(
            experiment_id="fixture-hard-null",
            adapter=FixtureDiscoveryAdapter("proposer", POSITIVE),
        ),
        discovery.evaluate_model(
            experiment_id="fixture-hard-null",
            adapter=FixtureDiscoveryAdapter("skeptic", NULL),
        ),
    )
    return role, runs


def test_holdout_is_fresh_balanced_and_freezes_both_controls():
    validate_hard_null_holdout_spec()
    assert HOLDOUT_SPEC["positive_count"] == HOLDOUT_SPEC["hard_null_count"] == 8
    assert HOLDOUT_SPEC["materiality_control_hash"] == MATERIALITY_CONTROL_HASH
    assert HOLDOUT_SPEC["receipt_quality_control_hash"] == RECEIPT_QUALITY_CONTROL_HASH
    old_cases = (*OLD_DISCOVERY_CASES, *OLD_COORDINATOR_CASES)
    assert not ({case.item_id for case in CASES} & {case.item_id for case in old_cases})
    assert not ({case.prompt for case in CASES} & {case.prompt for case in old_cases})


def test_blind_surface_hides_truth_and_counterbalances_positions_by_class():
    role, runs = _role_and_runs()
    surface = build_hard_null_surface(role_artifact=role, model_runs=runs)
    validate_hard_null_surface(surface, role_artifact=role, model_runs=runs)
    public = json.dumps(surface["public_batches"], sort_keys=True)
    assert "expected_state" not in public and "construction_basis" not in public
    assert "proposer" not in public and "skeptic" not in public
    positives = [
        FIRST_POSITION_ROLE[index]
        for index, case in enumerate(CASES) if case.expected_state == POSITIVE
    ]
    nulls = [
        FIRST_POSITION_ROLE[index]
        for index, case in enumerate(CASES) if case.expected_state == NULL
    ]
    assert positives.count("PROPOSER") == nulls.count("PROPOSER") == 4


def test_positive_decision_cannot_bypass_receipt_quality_control():
    role, runs = _role_and_runs()
    surface = build_hard_null_surface(role_artifact=role, model_runs=runs)
    runtime = HardNullAmbiguityCoordinatorRuntime(surface=surface)
    task = runtime._task(
        "fixture", FixtureHardNullCoordinatorAdapter(),
        surface["public_batches"][0],
        tuple(
            item["coordination_item_id"]
            for item in surface["public_batches"][0]["items"]
        ),
    )
    adapter = FixtureHardNullCoordinatorAdapter()
    payload = adapter.invoke(task)["result"]
    positive = next(item for item in payload["decisions"] if item["final_state"] == POSITIVE)
    for assessment in positive["receipt_assessments"]:
        assessment.update({
            "quality_state": "INCOMPLETE",
            "task_grounded": False,
            "rivals_distinct": False,
            "output_sensitive": False,
        })
    with pytest.raises(ValueError, match="positive_requires_material_support"):
        validate_hard_null_coordinator_payload(
            payload,
            batch_id=task.inputs["batch"]["batch_id"],
            item_ids=tuple(
                item["coordination_item_id"] for item in task.inputs["batch"]["items"]
            ),
            evidence_refs=runtime.evidence_refs,
        )


def test_fixture_closes_hard_null_gates_without_predecessor_label_authority():
    role, runs = _role_and_runs()
    surface = build_hard_null_surface(role_artifact=role, model_runs=runs)
    adapter = FixtureHardNullCoordinatorAdapter()
    coordinator_run = HardNullAmbiguityCoordinatorRuntime(surface=surface).evaluate(
        experiment_id="fixture-hard-null", adapter=adapter,
    )
    artifact = build_hard_null_artifact(
        experiment_id="fixture-hard-null",
        role_artifact=role,
        model_runs=runs,
        surface=surface,
        coordinator_run=coordinator_run,
    )
    validate_hard_null_artifact(artifact, role_artifact=role)
    report = artifact["report"]
    assert report["fixed_strategy_profiles"]["OR_POSITIVE"]["balanced_accuracy"] == 0.5
    assert report["coordinator_profile"]["balanced_accuracy"] == 1.0
    assert report["candidate_state"] == "HARD_NULL_COORDINATOR_VALIDATION_CANDIDATE"
    assert all(report["gate_results"].values())
    assert report["predecessor_label_tuning"] is False
    assert all(
        item["predecessor_labels"] == "WITHHELD_AND_FORBIDDEN"
        for item in adapter.seen_inputs
    )


def test_control_or_artifact_tamper_fails_closed():
    role, runs = _role_and_runs()
    surface = build_hard_null_surface(role_artifact=role, model_runs=runs)
    tampered_surface = deepcopy(surface)
    tampered_surface["materiality_control_hash"] = "0" * 64
    with pytest.raises(ValueError, match="surface_hash_invalid"):
        validate_hard_null_surface(
            tampered_surface, role_artifact=role, model_runs=runs,
        )
    run = HardNullAmbiguityCoordinatorRuntime(surface=surface).evaluate(
        experiment_id="fixture-hard-null", adapter=FixtureHardNullCoordinatorAdapter(),
    )
    artifact = build_hard_null_artifact(
        experiment_id="fixture-hard-null",
        role_artifact=role,
        model_runs=runs,
        surface=surface,
        coordinator_run=run,
    )
    tampered_artifact = deepcopy(artifact)
    tampered_artifact["report"]["selection_authority"] = True
    with pytest.raises(ValueError, match="artifact_hash_invalid"):
        validate_hard_null_artifact(tampered_artifact, role_artifact=role)
