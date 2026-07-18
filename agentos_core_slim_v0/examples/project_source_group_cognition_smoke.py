"""Live P0-P5 smoke test against an archived, evidence-rich project source.

The source pack is read-only. Runtime receipts and manifests are written under
the configured output directory, which defaults to the repository's ignored
``outputs`` tree.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE_ROOT.parent
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    AgendaCandidate,
    AgentDescriptor,
    AgentRegistry,
    AgentRoleRequirement,
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
    CascadingInvalidationGraph,
    ClaimCandidate,
    CognitionRunObservation,
    CreditEvent,
    CreditLedger,
    DependencyEdge,
    EndogenousAgendaLoop,
    EpistemicReviewProtocol,
    GroupCognitionEvalHarness,
    JsonlCreditEventStore,
    KnowledgeNode,
    ObjectionReceipt,
    OpenProblem,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
    ProviderCapabilityProfile,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    ReplicationReceipt,
)


SOURCE_ENTRIES = (
    "LIFE_COG3R_MachineVerdict_v0_1.json",
    "LIFE_COG3R_IndependentQA_v0_1.json",
    "LIFE_COG3R_PM_Summary_v0_1.md",
    "LIFE_COG3R_Receipt_v0_1.md",
)

EXPECTED_CLASSIFICATION = "FAIL_NEGATIVE_CONTROLS"
EXPECTED_LOCAL_RULES = {"DayNight", "HighLife"}
BOUNDED_CLAIM_STATEMENT = (
    "Within LIFE_COG3R, the frozen G4 generalization-gap comparison recorded positive results in DayNight and "
    "HighLife, while no overall retention, causal, or aligned-Cbit conclusion passed."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _json_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hash_bytes(encoded)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def load_source_dossier(source_pack: Path, gate_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_pack = source_pack.resolve()
    gate_file = gate_file.resolve()
    if not source_pack.is_file() or not gate_file.is_file():
        raise FileNotFoundError("source_pack_and_gate_file_required")

    inventory = [
        {"path": str(source_pack), "sha256": _hash_bytes(source_pack.read_bytes()), "kind": "source_pack"},
        {"path": str(gate_file), "sha256": _hash_bytes(gate_file.read_bytes()), "kind": "frozen_gate"},
    ]
    with zipfile.ZipFile(source_pack) as archive:
        missing = [entry for entry in SOURCE_ENTRIES if entry not in archive.namelist()]
        if missing:
            raise ValueError(f"source_pack_entries_missing:{','.join(missing)}")
        entry_bytes = {entry: archive.read(entry) for entry in SOURCE_ENTRIES}
    for entry, data in entry_bytes.items():
        inventory.append(
            {
                "path": f"{source_pack}#{entry}",
                "sha256": _hash_bytes(data),
                "kind": "source_entry",
            }
        )

    machine_verdict = json.loads(entry_bytes[SOURCE_ENTRIES[0]])
    independent_qa = json.loads(entry_bytes[SOURCE_ENTRIES[1]])
    gates = json.loads(gate_file.read_text(encoding="utf-8"))
    dossier = {
        "source_project": "LIFE_COG3R",
        "evidence_coordinate": "Internal Project Evidence",
        "frozen_acceptance_gates": gates,
        "machine_verdict": machine_verdict,
        "independent_structural_qa": independent_qa,
        "pm_summary": entry_bytes[SOURCE_ENTRIES[2]].decode("utf-8"),
        "execution_receipt": entry_bytes[SOURCE_ENTRIES[3]].decode("utf-8"),
        "source_refs": [item["path"] for item in inventory],
    }
    return dossier, inventory


def _parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("provider_response_contains_no_json_object")
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("provider_response_json_not_object")
    return parsed


@dataclass(frozen=True)
class LiveProviderSpec:
    provider_id: str
    model_id: str
    endpoint: str
    api_key_env: str
    task_kind: str
    max_tokens: int
    extra_body: dict[str, Any]


class OpenAICompatibleJsonAdapter:
    """Small smoke-only adapter; credentials remain in environment variables."""

    def __init__(self, spec: LiveProviderSpec) -> None:
        self.spec = spec
        self.profile = ProviderCapabilityProfile(
            provider_id=spec.provider_id,
            model_id=spec.model_id,
            task_kinds=(spec.task_kind,),
            supports_thinking_mode=bool(spec.extra_body.get("thinking")),
            max_timeout_seconds=120,
        )

    def invoke(self, task: ProviderCognitiveTask) -> dict[str, Any]:
        api_key = os.environ.get(self.spec.api_key_env, "")
        if not api_key:
            raise RuntimeError(f"provider_api_key_missing:{self.spec.api_key_env}")
        required = task.expected_schema.get("required", [])
        user_prompt = (
            f"Objective:\n{task.objective}\n\n"
            f"Return one JSON object matching this field contract exactly:\n{json.dumps(task.expected_schema, indent=2)}\n"
            "Use JSON booleans for boolean fields, arrays for array fields, and numbers for number fields. "
            "Preserve exact source labels and cite only supplied source_refs.\n\n"
            f"Inputs:\n{json.dumps(task.inputs, indent=2, sort_keys=True)}"
        )
        payload = {
            "model": self.spec.model_id,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are one bounded AgentOS cognitive role. Treat source records as internal project evidence, "
                        "do not upgrade proxies into ontology, and do not erase negative results. Output JSON only."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "max_tokens": self.spec.max_tokens,
            "response_format": {"type": "json_object"},
            **self.spec.extra_body,
        }
        response = self._post(payload, api_key)
        message = response["choices"][0]["message"]
        result = _parse_json_content(message.get("content") or "")
        return {
            "result": result,
            "usage": response.get("usage") or {},
            "provenance_refs": task.allowed_evidence,
        }

    def _post(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        try:
            return self._post_once(payload, api_key)
        except urllib.error.HTTPError as exc:
            if exc.code != 400 or "response_format" not in payload:
                raise
            fallback = dict(payload)
            fallback.pop("response_format", None)
            return self._post_once(fallback, api_key)

    def _post_once(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        request = urllib.request.Request(
            self.spec.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))


def _schema(required: tuple[str, ...], arrays: tuple[str, ...], objects: tuple[str, ...] = ()) -> dict[str, Any]:
    properties: dict[str, dict[str, str]] = {}
    for field in arrays:
        properties[field] = {"type": "array"}
    for field in objects:
        properties[field] = {"type": "object"}
    for field in required:
        if field not in properties and field not in {
            "confidence",
            "rival_set_coverage",
            "expected_cbit_gain",
            "falsifiability",
            "tractability",
            "urgency",
            "novelty",
            "negative_transfer_risk",
            "normalized_cost",
            "retention_gate_supported",
            "negative_controls_passed",
            "highest_conclusion_allowed",
            "boundary_respected",
        }:
            properties[field] = {"type": "string"}
    for field in (
        "confidence",
        "rival_set_coverage",
        "expected_cbit_gain",
        "falsifiability",
        "tractability",
        "urgency",
        "novelty",
        "negative_transfer_risk",
        "normalized_cost",
    ):
        if field in required:
            properties[field] = {"type": "number"}
    for field in (
        "retention_gate_supported",
        "negative_controls_passed",
        "highest_conclusion_allowed",
        "boundary_respected",
    ):
        if field in required:
            properties[field] = {"type": "boolean"}
    return {"required": list(required), "properties": properties}


def _task(
    task_id: str,
    task_kind: str,
    objective: str,
    inputs: dict[str, Any],
    source_refs: list[str],
    required: tuple[str, ...],
    arrays: tuple[str, ...],
    objects: tuple[str, ...] = (),
) -> ProviderCognitiveTask:
    return ProviderCognitiveTask(
        task_id=task_id,
        task_kind=task_kind,
        objective=objective,
        inputs=inputs,
        allowed_evidence=source_refs,
        expected_schema=_schema(required, arrays, objects),
        timeout_seconds=120,
        freshness_requirement="archived_project_source_frozen_2026-07-15",
    )


def _canonical_rules(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    labels = set()
    for value in values:
        text = str(value)
        for label in EXPECTED_LOCAL_RULES:
            if label in text:
                labels.add(label)
    return labels


def score_fact_alignment(result: dict[str, Any]) -> tuple[float, dict[str, bool]]:
    rules = _canonical_rules(result.get("local_generalization_gap_supported_rules"))
    checks = {
        "classification_exact": result.get("source_machine_classification") == EXPECTED_CLASSIFICATION,
        "retention_gate_not_promoted": result.get("retention_gate_supported") is False,
        "local_g4_rules_preserved": rules == EXPECTED_LOCAL_RULES,
        "negative_controls_failure_preserved": result.get("negative_controls_passed") is False,
        "no_highest_conclusion_fabricated": result.get("highest_conclusion_allowed") is False,
        "ontology_boundary_respected": result.get("boundary_respected") is True,
    }
    return round(sum(checks.values()) / len(checks), 12), checks


def _require_completed(role: str, envelope: Any, output_dir: Path) -> dict[str, Any]:
    payload = envelope.as_dict()
    _write_json(output_dir / "provider_receipts" / f"{role}.json", payload)
    if not envelope.semantic_result_present or envelope.normalized_result is None:
        raise RuntimeError(f"provider_role_failed:{role}:{envelope.status}:{','.join(envelope.validation_errors)}")
    return envelope.normalized_result


def _route_with_schema_retry(task: ProviderCognitiveTask, spec: LiveProviderSpec) -> Any:
    return ProviderTaskRouter(
        [OpenAICompatibleJsonAdapter(spec), OpenAICompatibleJsonAdapter(spec)]
    ).route(task)


def _unit_value(result: dict[str, Any], field: str) -> float:
    value = result.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"provider_unit_value_invalid:{field}")
    return float(value)


def build_member_observations(
    role_results: dict[str, dict[str, Any]],
    fact_scores: dict[str, tuple[float, dict[str, bool]]],
    agent_ids: dict[str, str],
    provider_receipt_refs: dict[str, str],
) -> tuple[CognitionRunObservation, ...]:
    return tuple(
        CognitionRunObservation(
            subject_id=agent_ids[role],
            quality_score=score,
            hypotheses=tuple(str(item) for item in role_results[role].get("hypotheses", [])),
            evidence_refs=(provider_receipt_refs[role],),
        )
        for role, (score, _checks) in fact_scores.items()
        if role != "synthesizer"
    )


def replicator_consistency_assertions(source_refs: list[str]) -> list[dict[str, Any]]:
    evidence_refs = list(source_refs)
    expected_values = (
        ("source-classification", "source_machine_classification", "equals", EXPECTED_CLASSIFICATION),
        ("retention-gate", "retention_gate_supported", "equals", False),
        ("negative-controls", "negative_controls_passed", "equals", False),
        ("highest-conclusion", "highest_conclusion_allowed", "equals", False),
        ("boundary", "boundary_respected", "equals", True),
        ("local-rule-count", "local_generalization_gap_supported_rules", "length_equals", 2),
        ("overbroad-outcome", "replication_outcome", "equals", "FAILED"),
        ("bounded-outcome", "bounded_claim_replication_outcome", "equals", "PASSED"),
    )
    return [
        {
            "assertion_id": assertion_id,
            "path": path,
            "operator": operator,
            "expected": expected,
            "evidence_refs": evidence_refs,
        }
        for assertion_id, path, operator, expected in expected_values
    ]


def run_smoke(source_pack: Path, gate_file: Path, output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dossier, source_inventory = load_source_dossier(source_pack, gate_file)
    _write_json(output_dir / "source_hash_inventory.json", source_inventory)
    source_refs = dossier["source_refs"]

    specs = {
        "generator": LiveProviderSpec(
            "deepseek",
            "deepseek-v4-flash",
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            "group_hypothesis_generation",
            2500,
            {"thinking": {"type": "disabled"}},
        ),
        "reviewer": LiveProviderSpec(
            "moonshot",
            "kimi-k2.5",
            "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY",
            "adversarial_epistemic_review",
            6000,
            {},
        ),
        "replicator": LiveProviderSpec(
            "deepseek",
            "deepseek-v4-pro",
            "https://api.deepseek.com/chat/completions",
            "DEEPSEEK_API_KEY",
            "independent_replication_interpretation",
            3000,
            {"thinking": {"type": "disabled"}},
        ),
        "synthesizer": LiveProviderSpec(
            "moonshot",
            "kimi-k2.6",
            "https://api.moonshot.cn/v1/chat/completions",
            "MOONSHOT_API_KEY",
            "group_synthesis_and_conflict_resolution",
            6000,
            {},
        ),
    }

    agents = AgentRegistry()
    role_names = {
        "generator": "HYPOTHESIS_GENERATOR",
        "reviewer": "ADVERSARIAL_REVIEWER",
        "replicator": "REPLICATOR",
        "synthesizer": "SYNTHESIZER",
    }
    for role, spec in specs.items():
        agents.register(
            AgentDescriptor(
                agent_id=f"{role}-{spec.model_id}",
                role=role_names[role],
                capabilities=("semantic_judgment", "source_grounded_json"),
                runner_id="codex-project-source-smoke",
                harness_id="openai-compatible-http-json",
                provider_id=f"{spec.provider_id}:{spec.model_id}",
                context_isolation_key=f"life-cog3r-smoke-{role}",
                allowed_evidence_scopes=("project://LIFE_COG3R",),
            )
        )
    team = agents.form_team(
        "life-cog3r-smoke-team",
        tuple(AgentRoleRequirement(role) for role in role_names.values()),
    )
    _write_json(output_dir / "p3_agent_team.json", team.as_dict())

    common_facts = (
        "Always return source_machine_classification, retention_gate_supported, "
        "local_generalization_gap_supported_rules, negative_controls_passed, "
        "highest_conclusion_allowed, and boundary_respected. The overbroad claim under test is: "
        "'LIFE_COG3R proves validation-gated retention improves future adaptation.'"
    )
    generator_required = (
        "hypotheses",
        "assumptions",
        "rival_explanations",
        "falsifiable_predictions",
        "evidence_refs",
        "confidence",
        "source_machine_classification",
        "retention_gate_supported",
        "local_generalization_gap_supported_rules",
        "negative_controls_passed",
        "highest_conclusion_allowed",
        "boundary_respected",
    )
    generator_task = _task(
        "life-cog3r-generator",
        specs["generator"].task_kind,
        f"Generate the narrowest defensible hypotheses and expose the overbroad claim. {common_facts}",
        {"source_dossier": dossier},
        source_refs,
        generator_required,
        ("hypotheses", "assumptions", "rival_explanations", "falsifiable_predictions", "evidence_refs", "local_generalization_gap_supported_rules"),
    )
    generator_envelope = _route_with_schema_retry(generator_task, specs["generator"])
    generator = _require_completed("generator", generator_envelope, output_dir)

    reviewer_required = (
        "objections",
        "strongest_falsifier",
        "rival_set_coverage",
        "evidence_refs",
        "recommended_epistemic_state",
        "confidence",
        "invalidation_roots",
        "adjudication_basis",
        "affected_scope",
        "revalidation_need",
        "source_machine_classification",
        "retention_gate_supported",
        "local_generalization_gap_supported_rules",
        "negative_controls_passed",
        "highest_conclusion_allowed",
        "boundary_respected",
    )
    reviewer_task = _task(
        "life-cog3r-reviewer",
        specs["reviewer"].task_kind,
        (
            "Adversarially review the overbroad claim against frozen gates. Set recommended_epistemic_state to "
            "FALSIFIED, PENDING, or SUPPORTED_BOUNDED. Identify invalidation roots without discarding bounded local results. "
            f"{common_facts}"
        ),
        {"source_dossier": dossier, "generator_receipt": generator},
        source_refs,
        reviewer_required,
        ("objections", "evidence_refs", "invalidation_roots", "local_generalization_gap_supported_rules"),
    )
    reviewer_envelope = _route_with_schema_retry(reviewer_task, specs["reviewer"])
    reviewer = _require_completed("reviewer", reviewer_envelope, output_dir)

    replicator_required = (
        "replication_outcome",
        "bounded_claim_replication_outcome",
        "gate_results",
        "deviations",
        "evidence_refs",
        "confidence",
        "source_machine_classification",
        "retention_gate_supported",
        "local_generalization_gap_supported_rules",
        "negative_controls_passed",
        "highest_conclusion_allowed",
        "boundary_respected",
    )
    replicator_task = _task(
        "life-cog3r-replicator",
        specs["replicator"].task_kind,
        (
            "Independently interpret the machine verdict and frozen gates without seeing the reviewer output. "
            "replication_outcome concerns the overbroad retention-improvement claim; bounded_claim_replication_outcome "
            "concerns only the two positive generalization-gap comparisons with no overall promotion. Use PASSED, FAILED, "
            f"or INCONCLUSIVE. {common_facts}"
        ),
        {"source_dossier": dossier},
        source_refs,
        replicator_required,
        ("deviations", "evidence_refs", "local_generalization_gap_supported_rules"),
        ("gate_results",),
    )
    cognition_layer = ProviderBackedRuntimeCognitionLayer()
    consistency_assertions = replicator_consistency_assertions(source_refs)
    replicator_envelope = _route_with_schema_retry(replicator_task, specs["replicator"])
    replicator = _require_completed("replicator_initial", replicator_envelope, output_dir)
    replicator_audit = cognition_layer.audit_operation(
        "independent_replication_interpretation",
        {
            "provider_support_receipt": replicator,
            "semantic_consistency_assertions": consistency_assertions,
        },
    )
    replicator_audit_history = [{"stage": "initial", "audit": replicator_audit}]
    if replicator_audit["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT:
        repair_task = _task(
            "life-cog3r-replicator-consistency-revalidation",
            specs["replicator"].task_kind,
            (
                "Revalidate the independent replication receipt after the runtime detected contradictions with frozen "
                "project evidence. Correct judgment fields only when required by the source dossier. The bounded claim "
                f"under test is exactly: '{BOUNDED_CLAIM_STATEMENT}' For this descriptive claim, PASSED means the frozen "
                "source records those two G4 results and the stated non-promotion boundary; it does not mean negative "
                "controls passed or that retention causally improved adaptation. Assess it separately from the overbroad "
                "retention-improvement claim. Return a complete replacement receipt. "
                f"{common_facts}"
            ),
            {
                "source_dossier": dossier,
                "prior_replication_receipt": replicator,
                "runtime_consistency_conflicts": replicator_audit["semantic_consistency"],
            },
            source_refs,
            replicator_required,
            ("deviations", "evidence_refs", "local_generalization_gap_supported_rules"),
            ("gate_results",),
        )
        replicator_envelope = _route_with_schema_retry(repair_task, specs["replicator"])
        replicator = _require_completed("replicator_revalidated", replicator_envelope, output_dir)
        replicator_audit = cognition_layer.audit_operation(
            "independent_replication_interpretation",
            {
                "provider_support_receipt": replicator,
                "semantic_consistency_assertions": consistency_assertions,
            },
        )
        replicator_audit_history.append({"stage": "revalidated", "audit": replicator_audit})
    _write_json(output_dir / "semantic_conflict_resolution.json", replicator_audit_history)
    if replicator_audit["status"] != PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT:
        raise RuntimeError("replicator_semantic_consistency_revalidation_failed")
    _write_json(output_dir / "provider_receipts" / "replicator.json", replicator_envelope.as_dict())

    synthesizer_required = (
        "converged_claims",
        "unresolved_conflicts",
        "minority_positions",
        "evidence_refs",
        "uncertainties",
        "final_overbroad_claim_state",
        "open_problems",
        "residual_rivals",
        "candidate_questions",
        "expected_cbit_gain",
        "scope",
        "falsifiability",
        "tractability",
        "urgency",
        "novelty",
        "negative_transfer_risk",
        "normalized_cost",
        "source_machine_classification",
        "retention_gate_supported",
        "local_generalization_gap_supported_rules",
        "negative_controls_passed",
        "highest_conclusion_allowed",
        "boundary_respected",
    )
    synthesizer_task = _task(
        "life-cog3r-synthesizer",
        specs["synthesizer"].task_kind,
        (
            "Synthesize the three isolated receipts. Reject or retain the overbroad claim, preserve only source-supported "
            "bounded claims, and propose one next open problem targeting the largest unresolved rival. All seven agenda "
            "scores must be numbers in [0,1]. final_overbroad_claim_state must be FALSIFIED, PENDING, or SUPPORTED_BOUNDED. "
            f"{common_facts}"
        ),
        {
            "source_dossier": dossier,
            "generator_receipt": generator,
            "reviewer_receipt": reviewer,
            "replicator_receipt": replicator,
        },
        source_refs,
        synthesizer_required,
        (
            "converged_claims",
            "unresolved_conflicts",
            "minority_positions",
            "evidence_refs",
            "uncertainties",
            "open_problems",
            "residual_rivals",
            "candidate_questions",
            "local_generalization_gap_supported_rules",
        ),
    )
    synthesizer_envelope = _route_with_schema_retry(synthesizer_task, specs["synthesizer"])
    synthesizer = _require_completed("synthesizer", synthesizer_envelope, output_dir)

    semantic_audits = {
        "generator": cognition_layer.audit_operation("group_hypothesis_generation", {"provider_support_receipt": generator}),
        "reviewer": cognition_layer.audit_operation("adversarial_epistemic_review", {"provider_support_receipt": reviewer}),
        "replicator": replicator_audit,
        "synthesizer": cognition_layer.audit_operation("group_synthesis_and_conflict_resolution", {"provider_support_receipt": synthesizer}),
        "agenda": cognition_layer.audit_operation("endogenous_problem_generation", {"provider_support_receipt": synthesizer}),
        "invalidation_root": cognition_layer.audit_operation("knowledge_invalidation_root_assessment", {"provider_support_receipt": reviewer}),
    }
    mechanical_audits = {
        operation_id: cognition_layer.audit_operation(operation_id, {"operation_id": operation_id})
        for operation_id in (
            "agent_registry_context_isolation",
            "group_metric_calculation",
            "epistemic_credit_ledger_projection",
            "dependency_invalidation_propagation",
        )
    }
    _write_json(output_dir / "provider_cognition_audits.json", {"semantic": semantic_audits, "mechanical": mechanical_audits})

    provider_receipt_refs = {
        role: str(output_dir / "provider_receipts" / f"{role}.json")
        for role in specs
    }
    overbroad_claim = ClaimCandidate(
        claim_id="life-cog3r-overbroad-retention-improvement",
        author_agent_id=team.by_role("HYPOTHESIS_GENERATOR").agent_id,
        statement="LIFE_COG3R proves validation-gated retention improves future adaptation.",
        research_object="validation_gated_parent_retention",
        observable_proxy="final_heldout_robustness_and_generalization_gap",
        metric="frozen_G3_and_G6_gates",
        scope="project://LIFE_COG3R",
        rival_explanations=tuple(str(item) for item in generator.get("rival_explanations", [])) or ("local_G4_only",),
        frozen_gate_ref=str(gate_file.resolve()),
        evidence_refs=tuple(source_refs),
    )
    objection_state = "SUSTAINED" if reviewer.get("recommended_epistemic_state") == "FALSIFIED" else "OPEN"
    objection = ObjectionReceipt(
        objection_id="life-cog3r-overclaim-objection",
        target_claim_id=overbroad_claim.claim_id,
        reviewer_agent_id=team.by_role("ADVERSARIAL_REVIEWER").agent_id,
        rival_explanation="The local G4 gap result does not satisfy G3 retention eligibility or G6 negative controls.",
        strongest_falsifier_ref=str(source_pack.resolve()) + "#LIFE_COG3R_MachineVerdict_v0_1.json",
        status=objection_state,
        evidence_refs=tuple(source_refs),
    )
    replication_outcome = str(replicator.get("replication_outcome", "INCONCLUSIVE")).upper()
    if replication_outcome not in {"PASSED", "FAILED", "INCONCLUSIVE"}:
        replication_outcome = "INCONCLUSIVE"
    overbroad_replication = ReplicationReceipt(
        replication_id="life-cog3r-overclaim-replication",
        target_claim_id=overbroad_claim.claim_id,
        replicator_agent_id=team.by_role("REPLICATOR").agent_id,
        independent_context_id="life-cog3r-smoke-replicator",
        outcome=replication_outcome,
        evidence_refs=tuple(source_refs),
        provider_support_receipt_refs=(provider_receipt_refs["replicator"],),
    )
    epistemic = EpistemicReviewProtocol()
    overbroad_decision = epistemic.assess(overbroad_claim, (objection,), (overbroad_replication,))

    bounded_claim = ClaimCandidate(
        claim_id="life-cog3r-bounded-generalization-gap",
        author_agent_id=team.by_role("SYNTHESIZER").agent_id,
        statement=BOUNDED_CLAIM_STATEMENT,
        research_object="project_scoped_generalization_gap",
        observable_proxy="G4 positive rule count and corrected comparisons",
        metric="frozen_G4_gate",
        scope="project://LIFE_COG3R",
        rival_explanations=("local_metric_without_retention_advantage",),
        frozen_gate_ref=str(gate_file.resolve()),
        evidence_refs=tuple(source_refs),
    )
    bounded_outcome = str(replicator.get("bounded_claim_replication_outcome", "INCONCLUSIVE")).upper()
    if bounded_outcome not in {"PASSED", "FAILED", "INCONCLUSIVE"}:
        bounded_outcome = "INCONCLUSIVE"
    bounded_replication = ReplicationReceipt(
        replication_id="life-cog3r-bounded-replication",
        target_claim_id=bounded_claim.claim_id,
        replicator_agent_id=team.by_role("REPLICATOR").agent_id,
        independent_context_id="life-cog3r-smoke-replicator",
        outcome=bounded_outcome,
        evidence_refs=tuple(source_refs),
        provider_support_receipt_refs=(provider_receipt_refs["replicator"],),
    )
    bounded_decision = epistemic.assess(bounded_claim, (), (bounded_replication,))
    _write_json(
        output_dir / "p1_epistemic_decisions.json",
        {"overbroad": overbroad_decision.as_dict(), "bounded": bounded_decision.as_dict()},
    )

    credit = CreditLedger(JsonlCreditEventStore(output_dir / "p2_credit_ledger.jsonl"))
    credit.append(
        CreditEvent(
            "life-cog3r-review-credit",
            team.by_role("ADVERSARIAL_REVIEWER").agent_id,
            "agent",
            "OBJECTION_SUSTAINED" if objection_state == "SUSTAINED" else "OBJECTION_REJECTED",
            f"epistemic://{overbroad_claim.claim_id}/{overbroad_decision.decision}",
            tuple(source_refs),
            source_claim_id=overbroad_claim.claim_id,
        )
    )
    credit.append(
        CreditEvent(
            "life-cog3r-replication-credit",
            team.by_role("REPLICATOR").agent_id,
            "agent",
            "RECEIPT_VALIDATED" if replication_outcome == "FAILED" else "RECEIPT_INVALIDATED",
            f"epistemic://{overbroad_claim.claim_id}/{overbroad_decision.decision}",
            tuple(source_refs),
            source_claim_id=overbroad_claim.claim_id,
        )
    )
    credit_profiles = {
        role: credit.profile(team.by_role(role_names[role]).agent_id).as_dict()
        for role in ("reviewer", "replicator")
    }
    _write_json(output_dir / "p2_credit_profiles.json", credit_profiles)

    role_results = {
        "generator": generator,
        "reviewer": reviewer,
        "replicator": replicator,
        "synthesizer": synthesizer,
    }
    fact_scores = {role: score_fact_alignment(result) for role, result in role_results.items()}
    member_observations = build_member_observations(
        role_results,
        fact_scores,
        {role: team.by_role(role_names[role]).agent_id for role in role_results},
        provider_receipt_refs,
    )
    synth_score, synth_checks = fact_scores["synthesizer"]
    overclaim_corrected = synthesizer.get("final_overbroad_claim_state") == "FALSIFIED"
    bounded_preserved = (
        _canonical_rules(synthesizer.get("local_generalization_gap_supported_rules")) == EXPECTED_LOCAL_RULES
        and bool(synthesizer.get("converged_claims"))
    )
    group_observation = CognitionRunObservation(
        subject_id=team.team_id,
        quality_score=synth_score,
        hypotheses=tuple(str(item) for item in synthesizer.get("converged_claims", [])),
        errors_exposed=2,
        errors_corrected=int(overclaim_corrected) + int(bounded_preserved),
        candidates_admitted=2,
        candidates_survived=int(bounded_preserved),
        negative_transfer_opportunities=1,
        negative_transfer_intercepts=int(overclaim_corrected),
        convergence_steps=4,
        evidence_refs=(provider_receipt_refs["synthesizer"],),
    )
    group_evaluation = GroupCognitionEvalHarness().evaluate(
        "life-cog3r-project-source-smoke",
        member_observations,
        group_observation,
    )
    _write_json(
        output_dir / "p0_group_evaluation.json",
        {
            "evaluation": group_evaluation.as_dict(),
            "role_fact_scores": {
                role: {"score": score, "checks": checks}
                for role, (score, checks) in fact_scores.items()
            },
        },
    )

    agenda = EndogenousAgendaLoop(minimum_priority=0.2)
    agenda.register_problem(
        OpenProblem(
            "life-cog3r-negative-control-mechanism",
            "Why do two local G4 comparisons survive while the required negative-control family fails?",
            "retention_generalization_and_negative_controls",
            "project://LIFE_COG3R",
            tuple(source_refs),
            tuple(str(item) for item in synthesizer.get("residual_rivals", [])),
        )
    )
    candidate_questions = synthesizer.get("candidate_questions") or synthesizer.get("open_problems") or []
    proposed_question = str(candidate_questions[0]) if candidate_questions else "Revalidate the failed negative-control family."
    agenda.propose(
        AgendaCandidate(
            "life-cog3r-next-negative-control-audit",
            "life-cog3r-negative-control-mechanism",
            proposed_question,
            "project://LIFE_COG3R",
            provider_receipt_refs["synthesizer"],
            tuple(source_refs),
            _unit_value(synthesizer, "expected_cbit_gain"),
            _unit_value(synthesizer, "falsifiability"),
            _unit_value(synthesizer, "tractability"),
            _unit_value(synthesizer, "urgency"),
            _unit_value(synthesizer, "novelty"),
            _unit_value(synthesizer, "negative_transfer_risk"),
            _unit_value(synthesizer, "normalized_cost"),
        )
    )
    agenda_selection = agenda.select_next()
    _write_json(output_dir / "p4_agenda_selection.json", agenda_selection.as_dict())

    invalidation = CascadingInvalidationGraph()
    invalidation.register_node(KnowledgeNode(overbroad_claim.claim_id, "claim", "project://LIFE_COG3R", tuple(source_refs)))
    invalidation.register_node(KnowledgeNode("life-cog3r-overbroad-report", "report", "project://LIFE_COG3R", tuple(source_refs)))
    invalidation.register_node(KnowledgeNode("life-cog3r-overbroad-memory", "memory", "project://LIFE_COG3R", tuple(source_refs)))
    invalidation.register_node(KnowledgeNode(bounded_claim.claim_id, "claim", "project://LIFE_COG3R", tuple(source_refs)))
    invalidation.add_dependency(DependencyEdge(overbroad_claim.claim_id, "life-cog3r-overbroad-report", "DERIVED_IN"))
    invalidation.add_dependency(
        DependencyEdge(overbroad_claim.claim_id, "life-cog3r-overbroad-memory", "RETAINED_AS", "QUARANTINE")
    )
    invalidation_receipt = None
    if overbroad_decision.decision == "FALSIFIED":
        invalidation_receipt = invalidation.invalidate(
            overbroad_claim.claim_id,
            reason="provider_backed_epistemic_review_falsified_overbroad_claim",
            adjudication_ref=f"epistemic://{overbroad_claim.claim_id}/{overbroad_decision.decision}",
            evidence_refs=tuple(source_refs),
        )
    invalidation_payload = {
        "receipt": invalidation_receipt.as_dict() if invalidation_receipt else None,
        "node_statuses": {
            node_id: invalidation.node(node_id).status
            for node_id in (
                overbroad_claim.claim_id,
                "life-cog3r-overbroad-report",
                "life-cog3r-overbroad-memory",
                bounded_claim.claim_id,
            )
        },
    }
    _write_json(output_dir / "p5_invalidation.json", invalidation_payload)

    gates = {
        "source_machine_classification_frozen": dossier["machine_verdict"].get("machine_classification") == EXPECTED_CLASSIFICATION,
        "all_provider_tasks_completed": all(
            envelope.semantic_result_present
            for envelope in (generator_envelope, reviewer_envelope, replicator_envelope, synthesizer_envelope)
        ),
        "all_semantic_support_audits_pass": all(
            audit["status"] in {PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT, PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT}
            for audit in semantic_audits.values()
        ),
        "all_mechanical_boundaries_pass": all(
            audit["status"] == "PASS_MECHANICAL_RUNTIME_OPERATION" for audit in mechanical_audits.values()
        ),
        "team_context_isolated": team.context_isolated,
        "overbroad_claim_falsified": overbroad_decision.decision == "FALSIFIED",
        "bounded_local_claim_preserved": bounded_decision.decision == "SUPPORTED_BOUNDED",
        "synthesis_respects_boundary": synth_checks["ontology_boundary_respected"],
        "agenda_candidate_selected": agenda_selection.decision == "SELECT",
        "overbroad_dependents_blocked": (
            invalidation.node("life-cog3r-overbroad-report").status == "INVALIDATED"
            and invalidation.node("life-cog3r-overbroad-memory").status == "QUARANTINED"
        ),
        "bounded_claim_remains_active": invalidation.node(bounded_claim.claim_id).status == "ACTIVE",
    }
    result = {
        "smoke_id": "life-cog3r-project-source-p0-p5-smoke-v0-1",
        "created_at": _utc_now(),
        "status": "PASS" if all(gates.values()) else "FAIL",
        "source_project": "LIFE_COG3R",
        "evidence_coordinate": "Internal Project Evidence",
        "provider_independence": {
            "agent_count": 4,
            "provider_organizations": 2,
            "model_ids": [spec.model_id for spec in specs.values()],
            "context_isolation_keys": [agent.context_isolation_key for agent in team.agents],
            "limitation": "two_provider_organizations; OpenAI environment credential returned 401 before run",
        },
        "gates": gates,
        "group_evaluation": group_evaluation.as_dict(),
        "epistemic_decisions": {
            "overbroad": overbroad_decision.as_dict(),
            "bounded": bounded_decision.as_dict(),
        },
        "agenda_selection": agenda_selection.as_dict(),
        "invalidation": invalidation_payload,
        "test_boundary": (
            "This is a live provider-backed smoke test over internal project evidence. It validates integration and bounded "
            "semantic correction behavior, not production reliability or the ontology of group cognition."
        ),
    }
    result["result_hash"] = _json_hash(result)
    _write_json(output_dir / "smoke_result.json", result)

    manifest_files = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            manifest_files.append(
                {
                    "path": str(path.relative_to(output_dir)),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_bytes(path.read_bytes()),
                }
            )
    manifest = {
        "smoke_id": result["smoke_id"],
        "status": result["status"],
        "files": manifest_files,
    }
    manifest["manifest_hash"] = _json_hash(manifest)
    _write_json(output_dir / "manifest.json", manifest)
    return result


def default_paths() -> tuple[Path, Path]:
    source_root = (
        REPO_ROOT
        / "archive"
        / "20260717_legacy_research_line"
        / "workspace_materials"
        / "outputs"
        / "20260715_life_cog3r_retention_eligibility"
    )
    return (
        source_root / "run" / "LIFE_COG3R_RetentionEligibility_AlignedCbit_Return_Pack_v0_1.zip",
        source_root
        / "seed"
        / "LIFE_COG3R_RetentionEligibility_AlignedCbit_Seed_Pack_v0_1"
        / "specs"
        / "acceptance_gates_LIFE_COG3R_v0_1.json",
    )


def main() -> int:
    default_pack, default_gate = default_paths()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack", type=Path, default=default_pack)
    parser.add_argument("--gate-file", type=Path, default=default_gate)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "outputs" / f"group_cognition_smoke_{timestamp}",
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
    print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir.resolve()), "gates": result["gates"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
