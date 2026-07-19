import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgentDescriptor, ProviderCapabilityProfile, ProviderTaskRouter
from agentos_runtime import (
    CognitiveAgent,
    CognitiveDeliberationSession,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)


ROLES = (
    "HYPOTHESIS_GENERATOR",
    "ADVERSARIAL_REVIEWER",
    "REPLICATOR",
    "SYNTHESIZER",
)


PAYLOADS = {
    "HYPOTHESIS_GENERATOR": {
        "hypotheses": ["claim-a"],
        "assumptions": ["assumption-a"],
        "rival_explanations": ["rival-a"],
        "falsifiable_predictions": ["prediction-a"],
        "evidence_refs": ["evidence://source"],
        "confidence": 0.7,
    },
    "ADVERSARIAL_REVIEWER": {
        "objections": ["objection-a"],
        "strongest_falsifier": "evidence://source",
        "rival_set_coverage": 0.9,
        "evidence_refs": ["evidence://source"],
        "recommended_epistemic_state": "PENDING",
        "confidence": 0.8,
    },
    "REPLICATOR": {
        "replication_outcome": "INCONCLUSIVE",
        "gate_results": {"G1": False},
        "deviations": ["insufficient power"],
        "evidence_refs": ["evidence://source"],
        "confidence": 0.75,
    },
    "SYNTHESIZER": {
        "converged_claims": [],
        "unresolved_conflicts": ["claim-a remains unresolved"],
        "minority_positions": ["rival-a"],
        "evidence_refs": ["evidence://source"],
        "uncertainties": ["replication inconclusive"],
    },
}


class ProviderFixture:
    def __init__(self, provider_id, model_id, task_kind, payload):
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=model_id,
            task_kinds=(task_kind,),
            max_timeout_seconds=120,
        )
        self.payload = payload
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.payload,
            "usage": {"total_tokens": 100},
            "provenance_refs": task.allowed_evidence,
        }


def test_four_independent_provider_backed_agents_complete_formal_deliberation(tmp_path):
    agents = []
    adapters = {}
    providers = {}
    for index, role in enumerate(ROLES, start=1):
        descriptor = AgentDescriptor(
            agent_id=f"agent-{index}",
            role=role,
            capabilities=("semantic_judgment", "source_read"),
            runner_id=f"runner-{index}",
            harness_id=f"harness-{index}",
            provider_id=f"provider-{index}",
            context_isolation_key=f"context-{index}",
            allowed_evidence_scopes=("project://fixture",),
        )
        cognitive_agent = CognitiveAgent(
            descriptor,
            standard_role_contract(role),
            model_id=f"model-{index}",
            private_memory_namespace=f"memory-{index}",
            harness_capabilities=("source_read", f"role-action-{index}"),
            credit_subject_id=f"credit-{index}",
        )
        provider = ProviderFixture(
            descriptor.provider_id,
            cognitive_agent.model_id,
            cognitive_agent.contract.provider_operation_id,
            PAYLOADS[role],
        )
        agents.append(cognitive_agent)
        providers[role] = provider
        adapters[cognitive_agent.agent_id] = ProviderCognitiveAgentAdapter(
            f"adapter-{index}",
            ProviderTaskRouter([provider]),
        )

    session = CognitiveDeliberationSession(
        session_id="provider-integration",
        objective="Determine the narrowest source-supported claim.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        agents=tuple(agents),
        adapters=adapters,
        workspace_root=tmp_path / "private-workspaces",
        kernel_authorization_ref="kernel-authorization://fixture",
        consistency_assertions_by_role={
            "REPLICATOR": (
                {
                    "assertion_id": "replication-outcome-frozen",
                    "path": "replication_outcome",
                    "operator": "equals",
                    "expected": "INCONCLUSIVE",
                    "evidence_refs": ["gate://fixture"],
                },
            )
        },
    )

    result = session.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert result.candidate_state == "PENDING_EPISTEMIC_REVIEW"
    assert len(result.messages) == 4
    assert len(result.execution_receipts) == 4
    assert all(receipt.provider_invocation_receipt.get("receipt_hash") for receipt in result.execution_receipts)
    assert result.execution_receipts[2].provider_audit["status"] == "PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT"
    reviewer_inputs = providers["ADVERSARIAL_REVIEWER"].tasks[0].inputs["context"]["input_messages"]
    replicator_inputs = providers["REPLICATOR"].tasks[0].inputs["context"]["input_messages"]
    synthesizer_inputs = providers["SYNTHESIZER"].tasks[0].inputs["context"]["input_messages"]
    assert [item["message_type"] for item in reviewer_inputs] == ["HYPOTHESIS_PROPOSAL"]
    assert [item["message_type"] for item in replicator_inputs] == ["HYPOTHESIS_PROPOSAL"]
    assert [item["message_type"] for item in synthesizer_inputs] == [
        "HYPOTHESIS_PROPOSAL",
        "ADVERSARIAL_REVIEW",
        "REPLICATION_REPORT",
    ]
    assert session.verify_replay()["valid"] is True
