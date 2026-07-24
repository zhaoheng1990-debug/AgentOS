from copy import deepcopy
from pathlib import Path
import json
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_contracts import (  # noqa: E402
    TASK_KIND as COORDINATOR_TASK_KIND, validate_coordinator_payload,
)
from local_collective_cognition.ambiguity_coordinator_eval import (  # noqa: E402
    build_coordinator_artifact, validate_coordinator_artifact,
)
from local_collective_cognition.ambiguity_coordinator_fallback import (  # noqa: E402
    build_fallback_role_candidate, validate_fallback_role_candidate,
)
from local_collective_cognition.ambiguity_coordinator_holdout import (  # noqa: E402
    CASES, EVIDENCE_REFS, HOLDOUT_SPEC, validate_coordinator_holdout_spec,
)
from local_collective_cognition.ambiguity_coordinator_runtime import AmbiguityCoordinatorRuntime  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_surface import (  # noqa: E402
    FIRST_POSITION_ROLE, build_coordinator_surface, validate_coordinator_surface,
)
from local_collective_cognition.ambiguity_discovery_contracts import TASK_KIND as DISCOVERY_TASK_KIND  # noqa: E402
from local_collective_cognition.ambiguity_discovery_runtime import AmbiguityDiscoveryRuntime  # noqa: E402
from local_collective_cognition.provider_telemetry import (  # noqa: E402
    ProviderInvocationTelemetry, ProviderTelemetryLedger, hash_payload,
)
from local_collective_cognition.unstated_ambiguity_holdout import (  # noqa: E402
    CASES as OLD_CASES, NULL, POSITIVE,
)


class FixtureDiscoveryAdapter:
    def __init__(self, model_id, state):
        self.state = state
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-" + model_id, model_id=model_id,
            task_kinds=(DISCOVERY_TASK_KIND,), max_timeout_seconds=120,
        )
        self.telemetry_ledger = ProviderTelemetryLedger()
        self.seen_tasks = []

    def invoke(self, task):
        self.seen_tasks.append(task)
        item_id = task.inputs["public_task"]["item_id"]
        positive = self.state == POSITIVE
        payload = {
            "item_id": item_id, "discovery_state": self.state,
            "rival_a": "area" if positive else "", "rival_b": "perimeter" if positive else "",
            "decisive_contrast": "requested measure" if positive else "",
            "discriminating_question": "Which measure is intended?" if positive else "",
            "confidence": 0.8, "evidence_refs": list(task.allowed_evidence),
        }
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id="telemetry-" + task.task_id, provider_id=self.profile.provider_id,
            model_id=self.profile.model_id, backend="fixture", task_id=task.task_id,
            task_kind=task.task_kind, task_contract_hash=hash_payload({"task_id": task.task_id}),
            status="COMPLETED", input_tokens=10, output_tokens=10, cached_tokens=0,
            latency_ms=1, api_cost=0.0, tool_calls=0, tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence), output_hash=hash_payload(payload),
            thinking_present=False, thinking_char_count=0, thinking_hash="", error_type="",
        )
        self.telemetry_ledger.record(telemetry)
        return {"result": payload, "usage": {"input_tokens": 10, "output_tokens": 10},
                "provenance_refs": list(task.allowed_evidence)}


class FixtureCoordinatorAdapter:
    def __init__(self, provider_id="fixture-coordinator", model_id="fixture-kimi"):
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id, model_id=model_id,
            task_kinds=(COORDINATOR_TASK_KIND,), max_timeout_seconds=240,
        )
        self.seen_inputs = []

    def invoke(self, task):
        self.seen_inputs.append(task.inputs)
        batch = task.inputs["batch"]
        decisions = []
        for item in batch["items"]:
            source_id = item["public_task"]["item_id"]
            decisions.append({
                "coordination_item_id": item["coordination_item_id"],
                "final_state": POSITIVE if int(source_id[1:]) % 2 else NULL,
                "supported_position": "POSITION_A", "confidence": 0.9,
                "decision_note": "Fixture semantic decision.",
            })
        return {"result": {"batch_id": batch["batch_id"], "decisions": decisions,
                           "evidence_refs": list(task.allowed_evidence)},
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "provenance_refs": list(task.allowed_evidence)}


class FailingCoordinatorAdapter(FixtureCoordinatorAdapter):
    def invoke(self, task):
        raise RuntimeError("fixture_provider_unavailable")


def _sources_and_runs():
    judge_commitment = {"policy_candidate": {
        "primary_judge_provider_id": "fixture-coordinator",
        "primary_judge_model_id": "fixture-kimi",
        "secondary_judge_provider_id": "fixture-secondary",
        "secondary_judge_model_id": "fixture-deepseek",
        "escalation_action": "SECOND_INDEPENDENT_JUDGE_THEN_MODEL_PANEL_IF_CONFLICT",
    }}
    judge = {**judge_commitment, "artifact_hash": hash_payload(judge_commitment)}
    role_commitment = {
        "judge_calibration_artifact_hash": judge["artifact_hash"],
        "role_candidates": {
            "ambiguity_proposer": {"provider_id": "fixture-proposer", "model_id": "proposer"},
            "null_skeptic": {"provider_id": "fixture-skeptic", "model_id": "skeptic"},
            "semantic_coordinator": {
                "provider_id": "fixture-coordinator", "model_id": "fixture-kimi",
                "binding_state": "UNVALIDATED_FOR_AMBIGUITY_COORDINATION",
            },
        },
    }
    role = {**role_commitment, "artifact_hash": hash_payload(role_commitment)}
    runtime = AmbiguityDiscoveryRuntime(
        cases=CASES, holdout_spec=HOLDOUT_SPEC,
        spec_validator=validate_coordinator_holdout_spec, evidence_refs=EVIDENCE_REFS,
    )
    proposer_adapter = FixtureDiscoveryAdapter("proposer", POSITIVE)
    skeptic_adapter = FixtureDiscoveryAdapter("skeptic", NULL)
    runs = (
        runtime.evaluate_model(experiment_id="fixture", adapter=proposer_adapter),
        runtime.evaluate_model(experiment_id="fixture", adapter=skeptic_adapter),
    )
    return judge, role, runs, proposer_adapter, skeptic_adapter


def test_fresh_holdout_is_paired_balanced_and_does_not_reuse_predecessor():
    validate_coordinator_holdout_spec()
    assert HOLDOUT_SPEC["positive_count"] == HOLDOUT_SPEC["null_count"] == 6
    assert not ({case.item_id for case in CASES} & {case.item_id for case in OLD_CASES})
    assert not ({case.prompt for case in CASES} & {case.prompt for case in OLD_CASES})


def test_discovery_runtime_binds_fresh_evidence_without_changing_default_contract():
    _, _, runs, proposer, skeptic = _sources_and_runs()
    assert all(tuple(task.allowed_evidence) == EVIDENCE_REFS
               for task in proposer.seen_tasks + skeptic.seen_tasks)
    assert runs[0]["profile"]["positive_recall"] == 1.0
    assert runs[1]["profile"]["null_specificity"] == 1.0
    assert AmbiguityDiscoveryRuntime().evidence_refs != EVIDENCE_REFS


def test_surface_counterbalances_roles_and_hides_identity_from_public_batches():
    _, role, runs, _, _ = _sources_and_runs()
    surface = build_coordinator_surface(role_artifact=role, model_runs=runs)
    validate_coordinator_surface(surface, role_artifact=role, model_runs=runs)
    public = json.dumps(surface["public_batches"], sort_keys=True)
    assert "proposer" not in public and "skeptic" not in public and "fixture" not in public
    positives = [FIRST_POSITION_ROLE[index] for index, case in enumerate(CASES) if case.expected_state == POSITIVE]
    nulls = [FIRST_POSITION_ROLE[index] for index, case in enumerate(CASES) if case.expected_state == NULL]
    assert positives.count("PROPOSER") == nulls.count("PROPOSER") == 3


def test_compact_surface_changes_only_batching_and_remains_valid():
    _, role, runs, _, _ = _sources_and_runs()
    compact = build_coordinator_surface(role_artifact=role, model_runs=runs, batch_size=3)
    validate_coordinator_surface(compact, role_artifact=role, model_runs=runs)
    assert compact["batch_size"] == 3
    assert len(compact["public_batches"]) == 4
    assert all(len(batch["items"]) == 3 for batch in compact["public_batches"])


def test_coordinator_closes_fixture_gain_with_bounded_cost_and_no_authority():
    judge, role, runs, _, _ = _sources_and_runs()
    surface = build_coordinator_surface(role_artifact=role, model_runs=runs)
    adapter = FixtureCoordinatorAdapter()
    coordinator_run = AmbiguityCoordinatorRuntime(surface=surface).evaluate(
        experiment_id="fixture", adapter=adapter,
    )
    artifact = build_coordinator_artifact(
        experiment_id="fixture", role_artifact=role, judge_calibration_artifact=judge,
        model_runs=runs, surface=surface, coordinator_run=coordinator_run,
    )
    validate_coordinator_artifact(
        artifact, role_artifact=role, judge_calibration_artifact=judge,
    )
    report = artifact["report"]
    assert report["fixed_strategy_profiles"]["OR_POSITIVE"]["balanced_accuracy"] == 0.5
    assert report["coordinator_profile"]["balanced_accuracy"] == 1.0
    assert report["balanced_gain_vs_frozen_comparator"] == 0.5
    assert report["candidate_state"] == "COORDINATOR_GAIN_EVIDENCE_CANDIDATE"
    assert all(report["gate_results"].values())
    assert not report["selection_authority"] and not report["production_authority"]
    assert all(item["source_identity"] == "WITHHELD" for item in adapter.seen_inputs)


def test_coordinator_artifact_and_payload_fail_closed_on_tamper():
    judge, role, runs, _, _ = _sources_and_runs()
    surface = build_coordinator_surface(role_artifact=role, model_runs=runs)
    run = AmbiguityCoordinatorRuntime(surface=surface).evaluate(
        experiment_id="fixture", adapter=FixtureCoordinatorAdapter(),
    )
    artifact = build_coordinator_artifact(
        experiment_id="fixture", role_artifact=role, judge_calibration_artifact=judge,
        model_runs=runs, surface=surface, coordinator_run=run,
    )
    tampered = deepcopy(artifact)
    tampered["report"]["production_authority"] = True
    with pytest.raises(ValueError, match="artifact_hash_invalid"):
        validate_coordinator_artifact(tampered, role_artifact=role, judge_calibration_artifact=judge)
    payload = deepcopy(run["judgments"][0]["payload"])
    payload["decisions"].pop()
    batch = surface["public_batches"][0]
    with pytest.raises(ValueError, match="decision_count_invalid"):
        validate_coordinator_payload(
            payload, batch_id=batch["batch_id"],
            item_ids=tuple(item["coordination_item_id"] for item in batch["items"]),
            evidence_refs=(f"surface://{surface['surface_hash']}",),
        )


def test_missing_coordinator_surface_is_recorded_as_gate_failure_not_report_crash():
    judge, role, runs, _, _ = _sources_and_runs()
    surface = build_coordinator_surface(role_artifact=role, model_runs=runs)
    run = AmbiguityCoordinatorRuntime(surface=surface).evaluate(
        experiment_id="fixture", adapter=FailingCoordinatorAdapter(),
    )
    artifact = build_coordinator_artifact(
        experiment_id="fixture", role_artifact=role, judge_calibration_artifact=judge,
        model_runs=runs, surface=surface, coordinator_run=run,
    )
    assert artifact["report"]["candidate_state"] == "COORDINATOR_CALIBRATION_GATE_FAILED"
    assert artifact["report"]["uncertain_or_unavailable_rate"] == 1.0
    assert artifact["report"]["gate_results"]["complete_decision_surface"] is False


def test_secondary_coordinator_requires_hash_bound_primary_failures():
    judge, role, runs, _, _ = _sources_and_runs()
    primary_surface = build_coordinator_surface(role_artifact=role, model_runs=runs)
    failures = []
    for experiment_id in ("failure-1", "failure-2"):
        failed_run = AmbiguityCoordinatorRuntime(surface=primary_surface).evaluate(
            experiment_id=experiment_id, adapter=FailingCoordinatorAdapter(),
        )
        failures.append(build_coordinator_artifact(
            experiment_id=experiment_id, role_artifact=role,
            judge_calibration_artifact=judge, model_runs=runs,
            surface=primary_surface, coordinator_run=failed_run,
        ))
    fallback = build_fallback_role_candidate(
        primary_role_artifact=role, judge_calibration_artifact=judge,
        primary_failure_artifacts=failures,
    )
    validate_fallback_role_candidate(
        fallback, primary_role_artifact=role, judge_calibration_artifact=judge,
        primary_failure_artifacts=failures,
    )
    surface = build_coordinator_surface(role_artifact=fallback, model_runs=runs, batch_size=3)
    run = AmbiguityCoordinatorRuntime(surface=surface, max_attempts_per_batch=1).evaluate(
        experiment_id="fallback", adapter=FixtureCoordinatorAdapter(
            provider_id="fixture-secondary", model_id="fixture-deepseek",
        ),
    )
    artifact = build_coordinator_artifact(
        experiment_id="fallback", role_artifact=fallback,
        judge_calibration_artifact=judge, model_runs=runs,
        surface=surface, coordinator_run=run,
    )
    assert artifact["report"]["candidate_state"] == "COORDINATOR_GAIN_EVIDENCE_CANDIDATE"
    with pytest.raises(ValueError, match="two_failures_required"):
        build_fallback_role_candidate(
            primary_role_artifact=role, judge_calibration_artifact=judge,
            primary_failure_artifacts=failures[:1],
        )
