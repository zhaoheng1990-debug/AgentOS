import hashlib
import json
import sys
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))
TRIAL_EVIDENCE_REFS = ("evidence://selector-smoke/problem",)

from agentos_kernel import (  # noqa: E402
    CONTEXTUAL_POLICY_COMPARATORS,
    CONTEXTUAL_POLICY_ROLE_MAP,
    ExecutedProtocolFootprint,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    PolicyExecutionBundle,
    PolicyExecutionOutcome,
    ProviderTaskRouter,
    SelectionExecutionBudget,
)
from agentos_runtime import (  # noqa: E402
    ContextualOrganizationPolicyRuntime,
    SelectionExecutionFeedbackBridge,
)
from examples.contextual_organization_policy_selector_smoke import (  # noqa: E402
    StaticOrganizationProvider,
    _problem,
    _records,
    _registry,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def budget() -> OrganizationBudgetEnvelope:
    return OrganizationBudgetEnvelope(
        budget_ref="budget://feedback-bridge",
        max_roles=4,
        max_provider_calls=5,
        max_coordination_steps=4,
        max_normalized_cost=0.8,
    )


def risk() -> OrganizationRiskEnvelope:
    return OrganizationRiskEnvelope(
        risk_ref="risk://feedback-bridge",
        max_residual_risk=0.5,
        max_provider_uncertainty=0.4,
        max_anti_additive_signal=0.5,
        matched_evidence_required_above_risk=0.4,
        allow_unmatched_exploration=True,
        exploration_max_roles=2,
    )


def execution_budget(
    *,
    max_protocol_runs: int = 2,
    max_provider_calls_total: int = 20,
    max_normalized_cost_per_protocol: float = 0.8,
) -> SelectionExecutionBudget:
    return SelectionExecutionBudget.create(
        budget_ref="budget://feedback-execution",
        max_protocol_runs=max_protocol_runs,
        max_provider_calls_total=max_provider_calls_total,
        max_normalized_cost_per_protocol=max_normalized_cost_per_protocol,
    )


def selector(tmp_path, *, record_source=None):
    provider = StaticOrganizationProvider()
    return ContextualOrganizationPolicyRuntime(
        runtime_id="feedback-selector",
        project_scope="project://contextual-policy-selector-smoke",
        registry=_registry(),
        provider_router=ProviderTaskRouter([provider]),
        workspace_root=tmp_path,
        record_source=record_source,
    )


def selection(tmp_path, *, selection_id="feedback-selection", records=None):
    engine = selector(tmp_path)
    return engine.select_policy(
        selection_id=selection_id,
        problem=_problem(),
        records=_records() if records is None else records,
        evidence_tier="LIVE_PROJECT",
        budget=budget(),
        risk=risk(),
        kernel_authorization_ref="kernel://feedback-selector/select",
    )


class ScriptedFeedbackExecutor:
    adapter_id = "scripted-feedback-executor"

    def __init__(
        self,
        *,
        source_label: str,
        replace_selected_agent: bool = False,
        drift_surface: bool = False,
        drift_binding: bool = False,
        hidden_protocol_cost: float | None = None,
    ):
        self.source_label = source_label
        self.replace_selected_agent = replace_selected_agent
        self.drift_surface = drift_surface
        self.drift_binding = drift_binding
        self.hidden_protocol_cost = hidden_protocol_cost
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        selected = request.selected_policy_id
        comparator = CONTEXTUAL_POLICY_COMPARATORS[selected]
        source_hash = digest(self.source_label)
        surface_hash = digest("drifted-surface") if self.drift_surface else request.trial_surface_hash
        outcomes = []
        for protocol_id in (selected, comparator):
            roles = CONTEXTUAL_POLICY_ROLE_MAP[protocol_id]
            if protocol_id == selected:
                agent_ids = request.selected_agent_ids
                if self.replace_selected_agent:
                    agent_ids = ("replacement-agent", *agent_ids[1:])
                effectiveness, cbit, cost = 0.84, 0.78, 0.55
            else:
                agent_ids = tuple(f"comparator-{index}" for index in range(len(roles)))
                effectiveness, cbit, cost = 0.70, 0.60, 0.70
            outcomes.append(
                PolicyExecutionOutcome.create(
                    outcome_id=f"outcome-{request.bridge_run_id}-{protocol_id.lower()}",
                    protocol_id=protocol_id,
                    agent_ids=agent_ids,
                    roles=roles,
                    agent_binding_hash=(
                        request.selected_agent_binding_hash
                        if protocol_id == selected
                        and not self.replace_selected_agent
                        and not self.drift_binding
                        else digest(f"binding-{request.bridge_run_id}-{protocol_id}")
                    ),
                    project_scope=request.project_scope,
                    context_key=request.context_key,
                    evidence_tier=request.evidence_tier,
                    trial_group_id=request.trial_group_id,
                    trial_id=request.trial_id,
                    trial_surface_hash=surface_hash,
                    evidence_refs=request.trial_evidence_refs,
                    effectiveness_score=effectiveness,
                    observed_cbit_gain=cbit,
                    normalized_cost=cost,
                    provider_call_count=4,
                    convergence_steps=4,
                    errors_exposed=2,
                    errors_corrected=1,
                    negative_transfer_opportunities=2,
                    negative_transfer_intercepts=1,
                    harness_receipt_ref=f"harness://{request.bridge_run_id}/{protocol_id}",
                    harness_receipt_hash=digest(f"harness-{request.bridge_run_id}-{protocol_id}"),
                    execution_result_hash=digest(f"execution-{request.bridge_run_id}-{protocol_id}"),
                    source_result_hash=source_hash,
                    replay_valid=True,
                )
            )
        footprints = [
            ExecutedProtocolFootprint.create(
                protocol_id=item.protocol_id,
                provider_call_count=item.provider_call_count,
                normalized_cost=item.normalized_cost,
                execution_result_hash=item.execution_result_hash,
                harness_receipt_hash=item.harness_receipt_hash,
            )
            for item in outcomes
        ]
        if self.hidden_protocol_cost is not None:
            footprints.append(
                ExecutedProtocolFootprint.create(
                    protocol_id="FIXED_TEAM",
                    provider_call_count=3,
                    normalized_cost=self.hidden_protocol_cost,
                    execution_result_hash=digest("hidden-fixed-result"),
                    harness_receipt_hash=digest("hidden-fixed-harness"),
                )
            )
        return PolicyExecutionBundle.create(
            bridge_run_id=request.bridge_run_id,
            selection_receipt_hash=request.selection_receipt_hash,
            selected_policy_id=request.selected_policy_id,
            execution_adapter_id=self.adapter_id,
            outcomes=tuple(outcomes),
            executed_protocols=tuple(footprints),
            execution_replay={"valid": True, "source": self.source_label},
        )


def bridge(tmp_path):
    return SelectionExecutionFeedbackBridge(
        runtime_id="feedback-bridge",
        project_scope="project://contextual-policy-selector-smoke",
        workspace_root=tmp_path,
    )


def execute(engine, selected, *, index: int, executor=None):
    return engine.execute_and_admit(
        bridge_run_id=f"feedback-run-{index}",
        selection=selected,
        executor=executor or ScriptedFeedbackExecutor(source_label=f"source-{index}"),
        trial_group_id=f"feedback-group-{index}",
        trial_id=f"feedback-trial-{index}",
        trial_evidence_refs=TRIAL_EVIDENCE_REFS,
        execution_budget=execution_budget(),
        kernel_execution_authorization_ref=f"kernel://feedback-bridge/run-{index}",
    )


def test_two_execution_feedback_runs_become_matched_evidence_and_feed_selector(tmp_path):
    selected = selection(tmp_path / "initial-selector")
    engine = bridge(tmp_path / "bridge")

    first = execute(engine, selected, index=1)
    second = execute(engine, selected, index=2)
    no_synth_first = next(
        item for item in first.matched_evidence if item.policy_id == "DYNAMIC_NO_SYNTHESIZER"
    )
    no_synth_second = next(
        item for item in second.matched_evidence if item.policy_id == "DYNAMIC_NO_SYNTHESIZER"
    )

    assert no_synth_first.sufficient_matched_evidence is False
    assert no_synth_second.sufficient_matched_evidence is True
    assert no_synth_second.matched_pair_count == 2
    assert len(engine.organization_records(
        project_scope=selected.project_scope,
        context_key=selected.context_key,
        evidence_tier=selected.evidence_tier,
    )) == 4
    assert engine.verify_replay()["valid"] is True

    restarted = bridge(tmp_path / "bridge")
    assert restarted.verify_replay()["valid"] is True
    assert len(restarted.snapshot().receipts) == 2

    downstream = selector(tmp_path / "downstream-selector", record_source=restarted)
    downstream_selection = downstream.select_policy(
        selection_id="feedback-selection-downstream",
        problem=_problem(),
        evidence_tier="LIVE_PROJECT",
        budget=budget(),
        risk=risk(),
        kernel_authorization_ref="kernel://feedback-selector/downstream",
    )
    assert downstream_selection.kernel_decision.selected_policy_id == "DYNAMIC_NO_SYNTHESIZER"
    assert downstream_selection.kernel_decision.activation_mode == "AUTHORIZED_PROJECT_SCOPED"


def test_selected_agent_substitution_blocks_without_learning_record(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    executor = ScriptedFeedbackExecutor(source_label="substitution", replace_selected_agent=True)

    with pytest.raises(ValueError, match="selected_assignment_mismatch"):
        execute(engine, selected, index=1, executor=executor)

    assert engine.snapshot().receipts == ()
    assert engine.verify_replay()["valid"] is True
    assert "SELECTION_EXECUTION_FEEDBACK_BLOCKED" in (
        engine.public_store_path / "events.jsonl"
    ).read_text(encoding="utf-8")


def test_trial_surface_drift_blocks_before_record_admission(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    executor = ScriptedFeedbackExecutor(source_label="drift", drift_surface=True)

    with pytest.raises(ValueError, match="trial_surface_hash_mismatch"):
        execute(engine, selected, index=1, executor=executor)

    assert engine.snapshot().receipts == ()


def test_provider_or_context_binding_substitution_blocks_feedback(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    executor = ScriptedFeedbackExecutor(source_label="binding-drift", drift_binding=True)

    with pytest.raises(ValueError, match="selected_agent_binding_hash_mismatch"):
        execute(engine, selected, index=1, executor=executor)

    assert engine.snapshot().receipts == ()


def test_duplicate_trial_group_cannot_create_independent_evidence(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    execute(engine, selected, index=1)

    with pytest.raises(ValueError, match="duplicate_selection_feedback_trial_group"):
        engine.execute_and_admit(
            bridge_run_id="feedback-run-duplicate",
            selection=selected,
            executor=ScriptedFeedbackExecutor(source_label="duplicate"),
            trial_group_id="feedback-group-1",
            trial_id="feedback-trial-duplicate",
            trial_evidence_refs=TRIAL_EVIDENCE_REFS,
            execution_budget=execution_budget(),
            kernel_execution_authorization_ref="kernel://feedback-bridge/duplicate",
        )

    assert len(engine.snapshot().receipts) == 1


def test_tampered_feedback_event_chain_is_rejected_on_restart(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    execute(engine, selected, index=1)
    events_path = engine.public_store_path / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[-1])
    event["payload"]["receipt"]["request"]["context_key"] = "ctx-tampered"
    lines[-1] = json.dumps(event, sort_keys=True)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="selection_feedback_replay_invalid"):
        bridge(tmp_path / "bridge")


@pytest.mark.parametrize(
    ("budget_override", "expected_error"),
    (
        ({"max_protocol_runs": 1}, "execution_protocol_run_budget_exceeded"),
        ({"max_provider_calls_total": 7}, "execution_provider_call_budget_exceeded"),
        (
            {"max_normalized_cost_per_protocol": 0.69},
            "execution_normalized_cost_budget_exceeded",
        ),
    ),
)
def test_kernel_rejects_execution_outcomes_outside_explicit_budget(
    tmp_path, budget_override, expected_error
):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    values = {
        "max_protocol_runs": 2,
        "max_provider_calls_total": 20,
        "max_normalized_cost_per_protocol": 0.8,
        **budget_override,
    }

    with pytest.raises(ValueError, match=expected_error):
        engine.execute_and_admit(
            bridge_run_id="feedback-run-budget-block",
            selection=selected,
            executor=ScriptedFeedbackExecutor(source_label="budget-block"),
            trial_group_id="feedback-group-budget-block",
            trial_id="feedback-trial-budget-block",
            trial_evidence_refs=TRIAL_EVIDENCE_REFS,
            execution_budget=execution_budget(**values),
            kernel_execution_authorization_ref="kernel://feedback-bridge/budget-block",
        )

    assert engine.snapshot().receipts == ()


def test_kernel_applies_cost_limit_to_executed_but_unadmitted_protocol(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")

    with pytest.raises(
        ValueError,
        match="execution_normalized_cost_budget_exceeded:FIXED_TEAM",
    ):
        engine.execute_and_admit(
            bridge_run_id="feedback-run-hidden-cost",
            selection=selected,
            executor=ScriptedFeedbackExecutor(
                source_label="hidden-cost",
                hidden_protocol_cost=0.9,
            ),
            trial_group_id="feedback-group-hidden-cost",
            trial_id="feedback-trial-hidden-cost",
            trial_evidence_refs=TRIAL_EVIDENCE_REFS,
            execution_budget=execution_budget(
                max_protocol_runs=3,
                max_provider_calls_total=20,
            ),
            kernel_execution_authorization_ref="kernel://feedback-bridge/hidden-cost",
        )

    assert engine.snapshot().receipts == ()


def test_trial_evidence_must_belong_to_frozen_selection_surface(tmp_path):
    selected = selection(tmp_path / "selector")
    engine = bridge(tmp_path / "bridge")
    executor = ScriptedFeedbackExecutor(source_label="unselected-evidence")

    with pytest.raises(ValueError, match="trial_evidence_not_selected"):
        engine.execute_and_admit(
            bridge_run_id="feedback-run-unselected-evidence",
            selection=selected,
            executor=executor,
            trial_group_id="feedback-group-unselected-evidence",
            trial_id="feedback-trial-unselected-evidence",
            trial_evidence_refs=("evidence://outside-selection",),
            execution_budget=execution_budget(),
            kernel_execution_authorization_ref="kernel://feedback-bridge/unselected-evidence",
        )

    assert executor.requests == []
