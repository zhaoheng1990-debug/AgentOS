import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgentDescriptor, AgentRegistry, AgentRoleRequirement


def agent(agent_id, role, context, provider="deepseek", capabilities=("semantic_judgment",)):
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=capabilities,
        runner_id="codex",
        harness_id="local-harness",
        provider_id=provider,
        context_isolation_key=context,
        allowed_evidence_scopes=("project://fixture",),
    )


def test_registry_forms_context_isolated_epistemic_team():
    registry = AgentRegistry()
    registry.register(agent("generator", "HYPOTHESIS_GENERATOR", "ctx-generator"))
    registry.register(agent("reviewer", "ADVERSARIAL_REVIEWER", "ctx-reviewer"))
    registry.register(agent("replicator", "REPLICATOR", "ctx-replicator", provider="openai"))

    team = registry.form_team(
        "team-1",
        (
            AgentRoleRequirement("HYPOTHESIS_GENERATOR", ("semantic_judgment",)),
            AgentRoleRequirement("ADVERSARIAL_REVIEWER", ("semantic_judgment",)),
            AgentRoleRequirement("REPLICATOR", ("semantic_judgment",)),
        ),
    )

    assert team.context_isolated is True
    assert team.execution_authorized is False
    assert team.by_role("REPLICATOR").agent_id == "replicator"
    assert len({item.context_isolation_key for item in team.agents}) == 3


def test_shared_context_cannot_fake_independent_agents():
    registry = AgentRegistry()
    registry.register(agent("generator", "HYPOTHESIS_GENERATOR", "shared-context"))
    registry.register(agent("reviewer", "ADVERSARIAL_REVIEWER", "shared-context"))

    with pytest.raises(ValueError, match="no_context_isolated_team"):
        registry.form_team(
            "team-shared",
            (
                AgentRoleRequirement("HYPOTHESIS_GENERATOR"),
                AgentRoleRequirement("ADVERSARIAL_REVIEWER"),
            ),
        )


def test_capability_requirement_filters_agents():
    registry = AgentRegistry()
    registry.register(agent("reviewer", "ADVERSARIAL_REVIEWER", "ctx-reviewer"))

    with pytest.raises(ValueError, match="no_context_isolated_team"):
        registry.form_team(
            "team-capability",
            (AgentRoleRequirement("ADVERSARIAL_REVIEWER", ("source_retrieval",)),),
        )


def test_disabled_agent_is_not_selected_but_can_be_replaced_in_place():
    registry = AgentRegistry()
    descriptor = agent("replicator", "REPLICATOR", "ctx-replicator")
    registry.register(descriptor)
    registry.replace(replace(descriptor, enabled=False))

    assert registry.candidates(AgentRoleRequirement("REPLICATOR")) == ()


def test_distinct_provider_requirement_is_optional_and_enforceable():
    registry = AgentRegistry()
    registry.register(agent("generator", "HYPOTHESIS_GENERATOR", "ctx-generator", provider="deepseek"))
    registry.register(agent("reviewer", "ADVERSARIAL_REVIEWER", "ctx-reviewer", provider="deepseek"))

    with pytest.raises(ValueError, match="no_context_isolated_team"):
        registry.form_team(
            "team-provider-isolated",
            (
                AgentRoleRequirement("HYPOTHESIS_GENERATOR", require_distinct_provider=True),
                AgentRoleRequirement("ADVERSARIAL_REVIEWER", require_distinct_provider=True),
            ),
        )
